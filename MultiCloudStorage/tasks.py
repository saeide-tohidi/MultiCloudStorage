from azure.storage.blob import BlobServiceClient
from celery import shared_task
from django.apps import apps
from django.conf import settings
from libs.bitmovin_encoder import delete_encoded_video


@shared_task
def encode_video_by_bitmovin_on_azure_task(video_id):
    CloudEncodedVideo = apps.get_model("video", "CloudEncodedVideo")
    try:
        video = CloudEncodedVideo.objects.get(id=video_id)
        video.encode_video()
    except CloudEncodedVideo.DoesNotExist:
        pass


@shared_task
def encode_video_by_bitmovin_on_azure_task_every_five_min():
    CloudEncodedVideo = apps.get_model("video", "CloudEncodedVideo")
    videos_to_encode = CloudEncodedVideo.objects.filter(
        deleted_original_video=False, encoded=False
    )
    for video in videos_to_encode:
        try:
            encode_video_by_bitmovin_on_azure_task.delay(video.id)
        except Exception as e:
            pass


@shared_task
def delete_original_videos_from_azure_daily():
    CloudEncodedVideo = apps.get_model("video", "CloudEncodedVideo")
    videos_to_delete = CloudEncodedVideo.objects.filter(
        deleted_original_video=False, encoded=True
    )
    for video in videos_to_delete:
        try:
            delete_original_videos_from_azure.delay(file_path=video.video_file.name)
            video.deleted_original_video = True
            video.save(update_fields=["deleted_original_video"])
        except Exception as e:
            video.log = str(e)
            video.save(update_fields=["log"])


@shared_task
def delete_original_videos_from_azure(file_path):
    try:
        blob_service_client = BlobServiceClient(
            account_url=f"https://{settings.AZURE_ACCOUNT_NAME}.blob.core.windows.net",
            credential=settings.AZURE_ACCOUNT_KEY,
        )
        blob_client = blob_service_client.get_blob_client(
            container=settings.AZURE_CONTAINER, blob=file_path
        )
        blob_client.delete_blob()
    except Exception as e:
        print(e)


@shared_task
def delete_encoded_videos_from_azure(folder_prefix):
    try:
        blob_service_client = BlobServiceClient(
            account_url=f"https://{settings.AZURE_ACCOUNT_NAME}.blob.core.windows.net",
            credential=settings.AZURE_ACCOUNT_KEY,
        )
        container_client = blob_service_client.get_container_client(
            settings.AZURE_CONTAINER
        )

        blobs = container_client.list_blobs(name_starts_with=folder_prefix)

        for blob in blobs:
            blob_client = container_client.get_blob_client(blob.name)
            blob_client.delete_blob()

    except Exception as e:
        print(e)


@shared_task
def delete_encoded_video_from_bitmovin(encoding_id):
    try:
        delete_encoded_video(encoding_id=encoding_id)
    except Exception as e:
        print(e)
