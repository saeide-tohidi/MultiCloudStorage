from django.conf import settings
from storages.backends.azure_storage import AzureStorage
from storages.backends.s3boto3 import S3Boto3Storage


class FixJustInTime:
    def on_content_required(self, file):
        try:
            file.generate()
        except:
            pass

    def on_existence_required(self, file):
        try:
            file.generate()
        except:
            pass


class StaticStorage(S3Boto3Storage):
    bucket_name = "static"
    location = ""
    default_acl = "public-read"
    custom_domain = f"myc.nyc3.cdn.digitaloceanspaces.com/{bucket_name}"


class PublicMediaStorage(S3Boto3Storage):
    bucket_name = settings.PUBLIC_MEDIA_LOCATION
    location = ""
    default_acl = "public-read"
    custom_domain = f"myc.nyc3.cdn.digitaloceanspaces.com/{bucket_name}"
