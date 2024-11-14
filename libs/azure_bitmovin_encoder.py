import time
from azure.storage.blob import BlobServiceClient
from django.conf import settings
from bitmovin_api_sdk import BitmovinApi, BitmovinApiLogger
from bitmovin_api_sdk.models import *


def create_bitmovin_api():
    bitmovin_api = BitmovinApi(
        api_key=settings.BITMOVIN_API_KEY, logger=BitmovinApiLogger()
    )
    return bitmovin_api


def create_azure_input(bitmovin_api):
    azure_input = AzureInput(
        account_name=settings.AZURE_ACCOUNT_NAME,
        account_key=settings.AZURE_ACCOUNT_KEY,
        container=settings.AZURE_CONTAINER,
    )
    azure_input = bitmovin_api.encoding.inputs.azure.create(azure_input=azure_input)
    return azure_input.id


def create_azure_output(bitmovin_api):
    azure_output = AzureOutput(
        account_name=settings.AZURE_ACCOUNT_NAME,
        account_key=settings.AZURE_ACCOUNT_KEY,
        container=settings.AZURE_CONTAINER,
    )
    azure_output = bitmovin_api.encoding.outputs.azure.create(azure_output=azure_output)
    return azure_output.id


def create_encoding(bitmovin_api):
    encoding = Encoding(name="Encoding", cloud_region=CloudRegion.AUTO)
    encoding = bitmovin_api.encoding.encodings.create(encoding=encoding)
    return encoding.id


def create_video_streams(
    bitmovin_api, encoding_id, input_id, input_path, output_path, output_id
):
    video_configurations = [
        {"name": "H264 720p", "bitrate": 3000000, "width": 1280, "height": 720},
        {"name": "H264 720p 1", "bitrate": 4608000, "width": 1280, "height": 720},
        {"name": "H264 1080p 1", "bitrate": 6144000, "width": 1920, "height": 1080},
        {"name": "H264 720 2", "bitrate": 7987200, "width": 1920, "height": 1080},
    ]

    video_streams = []

    for config in video_configurations:
        video_configuration = H264VideoConfiguration(
            name=config["name"],
            bitrate=config["bitrate"],
            width=config["width"],
            height=config["height"],
            preset_configuration=PresetConfiguration.VOD_STANDARD,
        )

        video_configuration = bitmovin_api.encoding.configurations.video.h264.create(
            h264_video_configuration=video_configuration
        )

        video_stream_input = StreamInput(
            input_id=input_id,
            input_path=input_path,
            selection_mode=StreamSelectionMode.AUTO,
        )

        video_stream = Stream(
            input_streams=[video_stream_input], codec_config_id=video_configuration.id
        )
        video_stream = bitmovin_api.encoding.encodings.streams.create(
            encoding_id=encoding_id, stream=video_stream
        )
        video_streams.append(video_stream)

        acl_entry = AclEntry(permission=AclPermission.PUBLIC_READ)

        muxing_stream = MuxingStream(stream_id=video_stream.id)
        encoding_output = EncodingOutput(
            output_id=output_id, output_path=output_path + "video/", acl=[acl_entry]
        )
        video_muxing = Fmp4Muxing(
            segment_length=4.0, outputs=[encoding_output], streams=[muxing_stream]
        )
        bitmovin_api.encoding.encodings.muxings.fmp4.create(
            encoding_id=encoding_id, fmp4_muxing=video_muxing
        )

    return video_streams


def create_audio_stream(
    bitmovin_api, encoding_id, input_id, input_path, output_path, output_id
):
    audio_configuration = AacAudioConfiguration(
        name="AAC Audio Configuration",
        bitrate=128000,
        rate=48000,
    )

    audio_configuration = bitmovin_api.encoding.configurations.audio.aac.create(
        aac_audio_configuration=audio_configuration
    )

    audio_stream_input = StreamInput(
        input_id=input_id,
        input_path=input_path,
        selection_mode=StreamSelectionMode.AUTO,
    )

    audio_stream = Stream(
        input_streams=[audio_stream_input], codec_config_id=audio_configuration.id
    )

    audio_stream = bitmovin_api.encoding.encodings.streams.create(
        encoding_id=encoding_id, stream=audio_stream
    )

    acl_entry = AclEntry(permission=AclPermission.PUBLIC_READ)

    muxing_stream = MuxingStream(stream_id=audio_stream.id)
    encoding_output = EncodingOutput(
        output_id=output_id, output_path=output_path + "audio/", acl=[acl_entry]
    )
    audio_muxing = Fmp4Muxing(
        segment_length=4.0, outputs=[encoding_output], streams=[muxing_stream]
    )
    audio_muxing = bitmovin_api.encoding.encodings.muxings.fmp4.create(
        encoding_id=encoding_id, fmp4_muxing=audio_muxing
    )

    return audio_stream.id, audio_muxing.id


def create_manifests(
    bitmovin_api, encoding_id, output_path, output_id, audio_stream_id, audio_muxing_id
):
    acl_entry = AclEntry(permission=AclPermission.PUBLIC_READ)
    manifest_output = EncodingOutput(
        output_id=output_id, output_path=output_path, acl=[acl_entry]
    )

    # Create DASH Manifest
    dash_manifest = DashManifestDefault(
        manifest_name="stream.mpd",
        encoding_id=encoding_id,
        outputs=[manifest_output],
    )
    dash_manifest = bitmovin_api.encoding.manifests.dash.default.create(dash_manifest)

    # Create Audio Adaptation Set to DASH Manifest
    period = bitmovin_api.encoding.manifests.dash.periods.create(
        manifest_id=dash_manifest.id, period=Period()
    )

    audio_adaptation_set = AudioAdaptationSet(lang="en")
    audio_adaptation_set = (
        bitmovin_api.encoding.manifests.dash.periods.adaptationsets.audio.create(
            manifest_id=dash_manifest.id,
            period_id=period.id,
            audio_adaptation_set=audio_adaptation_set,
        )
    )

    dash_fmp4_representation = DashFmp4Representation(
        encoding_id=encoding_id,
        muxing_id=audio_muxing_id,
        segment_path=output_path + "audio/",
        type_=DashRepresentationType.TEMPLATE,
    )
    dash_fmp4_representation = bitmovin_api.encoding.manifests.dash.periods.adaptationsets.representations.fmp4.create(
        manifest_id=dash_manifest.id,
        period_id=period.id,
        adaptationset_id=audio_adaptation_set.id,
        dash_fmp4_representation=dash_fmp4_representation,
    )

    # Create HLS Manifest
    hls_manifest = HlsManifestDefault(
        manifest_name="stream.m3u8",
        encoding_id=encoding_id,
        outputs=[manifest_output],
        version=HlsManifestDefaultVersion.V1,
    )
    hls_manifest = bitmovin_api.encoding.manifests.hls.default.create(
        hls_manifest_default=hls_manifest
    )

    return dash_manifest.id, hls_manifest.id


def start_encoding(bitmovin_api, encoding_id, dash_manifest_id, hls_manifest_id):
    start_request = StartEncodingRequest(
        manifest_generator=ManifestGenerator.V2,
        vod_dash_manifests=[ManifestResource(manifest_id=dash_manifest_id)],
        vod_hls_manifests=[ManifestResource(manifest_id=hls_manifest_id)],
    )
    bitmovin_api.encoding.encodings.start(
        encoding_id=encoding_id, start_encoding_request=start_request
    )


def delete_original_video(video_file_name):
    blob_service_client = BlobServiceClient(
        account_url=f"https://{settings.AZURE_ACCOUNT_NAME}.blob.core.windows.net",
        credential=settings.AZURE_ACCOUNT_KEY,
    )
    blob_client = blob_service_client.get_blob_client(
        container=settings.AZURE_CONTAINER, blob=video_file_name
    )
    blob_client.delete_blob()
