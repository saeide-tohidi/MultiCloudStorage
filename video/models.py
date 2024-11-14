import re

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.db import models
from MultiCloudStorage.storage_backends import VideoAzureStorage
from libs.azure_bitmovin_encoder import *

from libs.bitmovin_encoder import start_encoding_video


class CloudEncodedVideo(models.Model):
    title = models.CharField(max_length=150)
    video_file = models.FileField(
        upload_to="videos/", storage=VideoAzureStorage(), null=True, blank=True
    )
    encoded = models.BooleanField(default=False)
    deleted_original_video = models.BooleanField(default=False)

    encoding_id = models.CharField(max_length=255, blank=True, null=True)
    dash_url = models.URLField(blank=True, null=True)
    hls_url = models.URLField(blank=True, null=True)

    log = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    def __str__(self):
        return f"{self.id}_{self.title}"

    # def save(self, *args, **kwargs):
    #     super().save(*args, **kwargs)
    #     if not self.encoded:
    #         encode_video_by_bitmovin_on_azure_task.delay(self.id)

    def sanitize_title(self, title):
        sanitized_title = "_".join(re.findall(r"\w+", title))
        if len(sanitized_title) > 25:
            sanitized_title = sanitized_title[:25]
        return sanitized_title

    def encode_video(self):
        try:
            sanitized_title = self.sanitize_title(self.title)
            output_name = f"{self.id}_{sanitized_title}"
            input_file_path = self.video_file.name

            encoding_id = start_encoding_video(input_file_path, output_name)

            self.encoding_id = encoding_id
            self.dash_url = (
                f"{settings.VIDEO_MEDIA_URL}/encoded_videos/{output_name}/stream.mpd"
            )
            self.hls_url = (
                f"{settings.VIDEO_MEDIA_URL}/encoded_videos/{output_name}/master.m3u8"
            )
            self.encoded = True
            self.deleted_original_video = False
            super().save(
                update_fields=[
                    "encoding_id",
                    "dash_url",
                    "hls_url",
                    "encoded",
                    "deleted_original_video",
                ]
            )

        except Exception as e:
            error_message = str(e)
            self.log = error_message
            super().save(update_fields=["log"])
            sentry_sdk.capture_exception(e)
