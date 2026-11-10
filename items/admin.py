from django.contrib import admin
from .models import Item,Match


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "item_name",
        "item_type",
        "location",
        "status",
        "created_at",
    )

    list_filter = ("item_type", "status")

    search_fields = ("item_name", "description", "location")
    
  

admin.site.register(Match)