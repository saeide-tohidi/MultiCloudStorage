from django.contrib import admin
from video.models import CloudEncodedVideo


class CloudEncodedVideoAdmin(admin.ModelAdmin):
    model = CloudEncodedVideo
    list_display = (
        "title",
        "encoded",
        "deleted_original_video",
        "encoding_id",
        "id",
    )
    readonly_fields = (
        "encoded",
        "deleted_original_video",
        "encoding_id",
        "dash_url",
        "hls_url",
        "created_at",
        "updated_at",
        "log",
    )


admin.site.register(CloudEncodedVideo, CloudEncodedVideoAdmin)
