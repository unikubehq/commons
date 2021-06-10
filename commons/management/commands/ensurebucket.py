from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **options):
        from storages.backends.s3boto3 import S3Boto3Storage

        storage = S3Boto3Storage()
        storage.bucket.create()
