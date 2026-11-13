
from django.db import models
from django.contrib.auth.models import User
import random
import string


class Item(models.Model):

    ITEM_TYPES = [
        ("LOST", "Lost"),
        ("FOUND", "Found"),
    ]

    STATUS_CHOICES = [
        ("OPEN", "Open"),
        ("MATCHED", "Matched"),
        ("RESOLVED", "Resolved"),
    ]

    item_code = models.CharField(
        max_length=12,
        blank=True,
        null=True,
        db_index=True
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="reported_items"
    )

    item_name = models.CharField(max_length=200)
    description = models.TextField()
    image = models.ImageField(upload_to="items/")

    item_type = models.CharField(
        max_length=5,
        choices=ITEM_TYPES
    )

    location = models.CharField(max_length=255)

    phone_number = models.CharField(
        max_length=20,
        blank=True
    )

    date = models.DateField()

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="OPEN"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    # 24-hour automatic deletion tracking
    resolved_at = models.DateTimeField(
        null=True,
        blank=True
    )

    # Location fields
    found_latitude = models.FloatField(null=True, blank=True)
    found_longitude = models.FloatField(null=True, blank=True)
    location_shared_at = models.DateTimeField(null=True, blank=True)

    current_latitude = models.FloatField(null=True, blank=True)
    current_longitude = models.FloatField(null=True, blank=True)
    is_location_sharing = models.BooleanField(default=False)
    location_updated_at = models.DateTimeField(null=True, blank=True)

    # AI image recognition
    image_embedding = models.JSONField(
        null=True,
        blank=True
    )

    def save(self, *args, **kwargs):

        # Generate a unique code for Lost items
        if self.item_type == "LOST" and not self.item_code:

            while True:
                code = "LF-" + ''.join(
                    random.choices(string.digits, k=6)
                )

                if not Item.objects.filter(item_code=code).exists():
                    self.item_code = code
                    break

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.item_name} - {self.item_type}"


class Match(models.Model):

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("CONFIRMED", "Confirmed"),
        ("REJECTED", "Rejected"),
    ]

    lost_item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        related_name="lost_matches"
    )

    found_item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        related_name="found_matches"
    )

    similarity_score = models.FloatField()

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="PENDING"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return (
            f"{self.lost_item.item_name} - "
            f"{self.found_item.item_name}"
        )
