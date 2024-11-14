import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "MultiCloudStorage.settings")
app = Celery("MultiCloudStorage")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks(["MultiCloudStorage.tasks"])
app.conf.timezone = "UTC"


app.conf.beat_schedule = {
    "delete_original_videos_midnight": {
        "task": "MultiCloudStorage.tasks.delete_original_videos_from_azure_daily",
        "schedule": crontab(hour=9, minute=0),
    },
    "encode_video_by_bitmovin_on_azure_task_every_five_min": {
        "task": "MultiCloudStorage.tasks.encode_video_by_bitmovin_on_azure_task_every_five_min",
        "schedule": 300.0,
    },
}
