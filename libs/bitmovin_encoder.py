import time

from bitmovin_api_sdk import (
    AacAudioConfiguration,
    AclEntry,
    AclPermission,
    BitmovinApi,
    BitmovinApiLogger,
    DashManifestDefault,
    DashManifestDefaultVersion,
    Encoding,
    EncodingOutput,
    Fmp4Muxing,
    H264VideoConfiguration,
    HlsManifestDefault,
    HlsManifestDefaultVersion,
    ManifestGenerator,
    ManifestResource,
    MessageType,
    MuxingStream,
    PresetConfiguration,
    StartEncodingRequest,
    Status,
    Stream,
    StreamInput,
    StreamSelectionMode,
    CloudRegion,
    AzureInput,
    AzureOutput,
)

from os import path
from django.conf import settings


BASE_OUTPUT_PATH = "encoded_videos/"

bitmovin_api = BitmovinApi(
    api_key=settings.BITMOVIN_API_KEY, logger=BitmovinApiLogger()
)


def start_encoding_video(input_file_path, output_name):
    encoding = _create_encoding(
        name=output_name,
        description="Encoding with HLS and DASH default manifests with multiple representations",
    )

    http_input = _create_http_input()

    input_file_path = input_file_path

    output = _create_s3_output()

    # ABR Ladder - H264
    video_configurations = [
        _create_h264_video_configuration(width=1280, height=720, bitrate=3000000),
        _create_h264_video_configuration(width=1280, height=720, bitrate=4608000),
        _create_h264_video_configuration(width=1920, height=1080, bitrate=6144000),
        _create_h264_video_configuration(width=1920, height=1080, bitrate=7987200),
    ]

    # create video streams and muxings
    for config in video_configurations:
        h264_video_stream = _create_stream(
            encoding=encoding,
            encoding_input=http_input,
            input_path=input_file_path,
            codec_configuration=config.id,
        )
        _create_fmp4_muxing(
            encoding=encoding,
            output=output,
            output_path="video/{0}".format(config.bitrate),
            stream=h264_video_stream,
            output_name=output_name,
        )

    # Audio - ACC
    audio_configurations = [
        _create_aac_audio_configuration(bitrate=192000),
        _create_aac_audio_configuration(bitrate=64000),
    ]

    # create audio streams and muxings
    for audio_config in audio_configurations:
        audio_stream = _create_stream(
            encoding=encoding,
            encoding_input=http_input,
            input_path=input_file_path,
            codec_configuration=audio_config.id,
        )
        _create_fmp4_muxing(
            encoding=encoding,
            output=output,
            output_path="audio/{0}".format(audio_config.bitrate),
            stream=audio_stream,
            output_name=output_name,
        )

    dash_manifest = _create_default_dash_manifest(
        encoding=encoding, output=output, output_path="", output_name=output_name
    )

    hls_manifest = _create_default_hls_manifest(
        encoding=encoding, output=output, output_path="", output_name=output_name
    )

    start_encoding_request = StartEncodingRequest(
        manifest_generator=ManifestGenerator.V2,
        vod_dash_manifests=[ManifestResource(manifest_id=dash_manifest.id)],
        vod_hls_manifests=[ManifestResource(manifest_id=hls_manifest.id)],
    )

    _execute_encoding(encoding=encoding, start_encoding_request=start_encoding_request)

    return encoding.id


def _execute_encoding(encoding, start_encoding_request):
    bitmovin_api.encoding.encodings.start(
        encoding_id=encoding.id, start_encoding_request=start_encoding_request
    )

    task = _wait_for_enoding_to_finish(encoding_id=encoding.id)

    while task.status is not Status.FINISHED and task.status is not Status.ERROR:
        task = _wait_for_enoding_to_finish(encoding_id=encoding.id)

    if task.status is Status.ERROR:
        _log_task_errors(task=task)
        raise Exception("Encoding failed")

    print("Encoding finished successfully")


def _wait_for_enoding_to_finish(encoding_id):
    time.sleep(120)
    task = bitmovin_api.encoding.encodings.status(encoding_id=encoding_id)
    return task


def _create_encoding(name, description):
    encoding = Encoding(
        name=name, description=description, cloud_region=CloudRegion.AUTO
    )
    return bitmovin_api.encoding.encodings.create(encoding=encoding)


def _create_http_input():
    http_input = AzureInput(
        account_name=settings.AZURE_ACCOUNT_NAME,
        account_key=settings.AZURE_ACCOUNT_KEY,
        container=settings.AZURE_CONTAINER,
    )

    return bitmovin_api.encoding.inputs.azure.create(azure_input=http_input)


def _create_s3_output():
    s3_output = AzureOutput(
        account_name=settings.AZURE_ACCOUNT_NAME,
        account_key=settings.AZURE_ACCOUNT_KEY,
        container=settings.AZURE_CONTAINER,
    )

    return bitmovin_api.encoding.outputs.azure.create(azure_output=s3_output)


def _create_h264_video_configuration(width, height, bitrate):
    config = H264VideoConfiguration(
        name="H.264 {0}p @ {1} Kbit/S".format(height, round(bitrate / 1000)),
        width=width,
        height=height,
        bitrate=bitrate,
        preset_configuration=PresetConfiguration.VOD_STANDARD,
    )

    return bitmovin_api.encoding.configurations.video.h264.create(
        h264_video_configuration=config
    )


def _create_stream(encoding, encoding_input, input_path, codec_configuration):
    stream_input = StreamInput(
        input_id=encoding_input.id,
        input_path=input_path,
        selection_mode=StreamSelectionMode.AUTO,
    )

    stream = Stream(input_streams=[stream_input], codec_config_id=codec_configuration)

    return bitmovin_api.encoding.encodings.streams.create(
        encoding_id=encoding.id, stream=stream
    )


def _create_aac_audio_configuration(bitrate):
    config = AacAudioConfiguration(
        name="AAC Audio @ {0} Kbps".format(round(bitrate / 1000)), bitrate=bitrate
    )

    return bitmovin_api.encoding.configurations.audio.aac.create(
        aac_audio_configuration=config
    )


def _create_fmp4_muxing(encoding, output, output_path, stream, output_name):
    muxing = Fmp4Muxing(
        segment_length=4.0,
        outputs=[
            _build_encoding_output(
                output=output, output_path=output_path, output_name=output_name
            )
        ],
        streams=[MuxingStream(stream_id=stream.id)],
    )

    return bitmovin_api.encoding.encodings.muxings.fmp4.create(
        encoding_id=encoding.id, fmp4_muxing=muxing
    )


def _create_default_dash_manifest(encoding, output, output_path, output_name):
    dash_manifest_default = DashManifestDefault(
        encoding_id=encoding.id,
        manifest_name="stream.mpd",
        version=DashManifestDefaultVersion.V1,
        outputs=[_build_encoding_output(output, output_path, output_name)],
    )

    return bitmovin_api.encoding.manifests.dash.default.create(
        dash_manifest_default=dash_manifest_default
    )


def _create_default_hls_manifest(encoding, output, output_path, output_name):
    hls_manifest_default = HlsManifestDefault(
        encoding_id=encoding.id,
        outputs=[_build_encoding_output(output, output_path, output_name)],
        name="master.m3u8",
        manifest_name="master.m3u8",
        version=HlsManifestDefaultVersion.V1,
    )
    return bitmovin_api.encoding.manifests.hls.default.create(
        hls_manifest_default=hls_manifest_default
    )


def _build_encoding_output(output, output_path, output_name):
    acl_entry = AclEntry(permission=AclPermission.PUBLIC_READ)

    return EncodingOutput(
        output_path=_build_absolute_path(
            relative_path=output_path, output_name=output_name
        ),
        output_id=output.id,
        acl=[acl_entry],
    )


def _build_absolute_path(relative_path, output_name):
    return path.join(BASE_OUTPUT_PATH, output_name, relative_path)


def _log_task_errors(task):
    if task is None:
        return

    filtered = [x for x in task.messages if x.type is MessageType.ERROR]

    for message in filtered:
        print(message.text)


def delete_encoded_video(encoding_id):
    try:
        bitmovin_api.encoding.encodings.delete(encoding_id=encoding_id)
    except Exception as e:
        return e
