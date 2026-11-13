
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from items.models import Item


class Command(BaseCommand):
    help = "Delete resolved items after 24 hours"

    def handle(self, *args, **options):

        cutoff_time = timezone.now() - timedelta(hours=24)

        expired_items = Item.objects.filter(
            status="RESOLVED",
            resolved_at__isnull=False,
            resolved_at__lte=cutoff_time
        )

        deleted_count = 0

        for item in expired_items.iterator():

            # Delete the uploaded image
            if item.image:
                item.image.delete(save=False)

            # Deleting the item also deletes related Match records
            item.delete()

            deleted_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully deleted {deleted_count} expired items."
            )
        )
