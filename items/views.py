from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required

from .models import Item, Match
from .forms import RegisterForm, ItemForm

from django.core.mail import send_mail

from .ai.image_matcher import get_image_embedding
from .matching_service import find_matching_items

from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from django.contrib.auth.decorators import user_passes_test

from django.contrib.auth.models import User

import json

from django.http import JsonResponse
from django.utils import timezone

from django.db.models import Q


# Home page
def home(request):
    return render(request, "items/home.html")


# Browse and search all open items
def browse_items(request):

    search_query = request.GET.get("q", "").strip()

    items = Item.objects.filter(status="OPEN")

    if search_query:
        items = items.filter(
            Q(item_name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(location__icontains=search_query) |
            Q(item_code__icontains=search_query)
        )

    return render(
        request,
        "items/browse_items.html",
        {
            "items": items.order_by("-created_at"),
            "search_query": search_query
        }
    )

@login_required
def item_details(request, item_id):

    item = get_object_or_404(Item, id=item_id)

    return render(
        request,
        "items/item_details.html",
        {"item": item}
    )
    
    
    
# Register a new user
def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)

        if form.is_valid():
            user = form.save(commit=False)
            user.email = form.cleaned_data["email"]
            user.save()

            login(request, user)

            return redirect("dashboard")

    else:
        form = RegisterForm()

    return render(
        request,
        "items/register.html",
        {"form": form}
    )


# Report a lost or found item
@login_required
def report_item(request):

    if request.method == "POST":

        form = ItemForm(request.POST, request.FILES)

        if form.is_valid():

            # Save the reported item
            item = form.save(commit=False)
            item.user = request.user
            item.save()

            try:
                # Generate image embedding
                embedding = get_image_embedding(item.image.path)
                
                
                item.image_embedding = embedding.squeeze().tolist()
                item.save(update_fields=["image_embedding"])

                # Find similar items
                possible_matches = find_matching_items(item)

                for result in possible_matches:

                    other_item = result["item"]
                    similarity = result["similarity"]

                 # Identify lost and found items
                if item.item_type == "LOST":
                    lost_item = item
                    found_item = other_item
                else:
                    lost_item = other_item
                    found_item = item

                # Assign the same code to both items
                if lost_item.item_code and not found_item.item_code:
                    found_item.item_code = lost_item.item_code
                    found_item.save(update_fields=["item_code"])

                    # Save match in database
                    match, created = Match.objects.get_or_create(
                        lost_item=lost_item,
                        found_item=found_item,
                        defaults={
                            "similarity_score": similarity,
                            "status": "PENDING",
                        },
                    )

                    # Send email only when a new match is created
                    if created and lost_item.user.email:

                        subject = "Possible Match Found - Lost and Found System"

                        message = f"""
Hello {lost_item.user.username},

Good news! We found a possible match for your lost item.

LOST ITEM DETAILS:
Item: {lost_item.item_name}
Location: {lost_item.location}
Date: {lost_item.date}

POSSIBLE FOUND ITEM DETAILS:
Item: {found_item.item_name}
Description: {found_item.description}
Location: {found_item.location}
Date: {found_item.date}

FOUND ITEM REPORTED BY:
Name: {found_item.user.get_full_name() or found_item.user.username}

Similarity Score: {similarity:.2f}

Please log in to your Lost and Found account
to review this possible match.

Note: This is an automatically generated possible match.
Please verify the item before claiming it.
"""

                        try:
                            send_mail(
                                subject,
                                message,
                                None,
                                [lost_item.user.email],
                                fail_silently=False,
                            )

                            print("Match notification email sent successfully.")

                        except Exception:
                            import logging
                            logging.exception("Email notification failed.")

            except Exception:
                import logging
                logging.exception(
                    "Image embedding or matching failed for item ID %s",
                    item.pk
                )

            if item.item_type == "FOUND":
                 return redirect("share_location", item_id=item.id)

        return redirect("my_reports")

    else:
        form = ItemForm()

    return render(
        request,
        "items/report_item.html",
        {"form": form}
    )
    


@login_required
def share_location(request, item_id):
    item = get_object_or_404(
        Item,
        id=item_id,
        user=request.user,
        item_type="FOUND"
    )

    return render(
        request,
        "items/share_location.html",
        {"item": item}
    )

# Display the logged-in user's reports
@login_required
def my_reports(request):
    items = Item.objects.filter(
        user=request.user
    ).order_by("-created_at")

    return render(
        request,
        "items/my_reports.html",
        {"items": items}
    )


# Display possible matches for the logged-in user
@login_required
def matches(request):
    my_items = Item.objects.filter(
        user=request.user
    )

    match_records = (
        Match.objects.filter(lost_item__in=my_items)
        | Match.objects.filter(found_item__in=my_items)
    )

    match_records = match_records.select_related(
        "lost_item",
        "found_item"
    ).order_by("-similarity_score")

    return render(
        request,
        "items/matches.html",
        {"matches": match_records}
    )


# Display the dashboard
@login_required
def dashboard(request):
    items = Item.objects.filter(
        user=request.user
    ).order_by("-created_at")[:5]

    return render(
        request,
        "items/dashboard.html",
        {"items": items}
    )


@login_required
def matches(request):
    my_items = Item.objects.filter(user=request.user)

    match_records = Match.objects.filter(
        lost_item__in=my_items
    ) | Match.objects.filter(
        found_item__in=my_items
    )

    match_records = match_records.select_related(
        "lost_item",
        "found_item"
    ).order_by("-similarity_score")

    return render(
        request,
        "items/matches.html",
        {"matches": match_records}
    )
    
    
    
@login_required
@require_POST
def confirm_match(request, match_id):
    match = get_object_or_404(Match, id=match_id)

    if match.lost_item.user != request.user:
        return redirect("matches")

    match.status = "CONFIRMED"
    match.save()

    match.lost_item.status = "MATCHED"
    match.lost_item.save()

    match.found_item.status = "MATCHED"
    match.found_item.save()

    return redirect("matches")


@login_required
@require_POST
def reject_match(request, match_id):
    match = get_object_or_404(Match, id=match_id)

    if match.lost_item.user != request.user:
        return redirect("matches")

    match.status = "REJECTED"
    match.save()

    return redirect("matches")



@user_passes_test(lambda user: user.is_staff, login_url="login")
def admin_dashboard(request):

    users = User.objects.all().order_by("-date_joined")

    lost_items = Item.objects.filter(item_type="LOST").order_by("-created_at")

    found_items = Item.objects.filter(item_type="FOUND").order_by("-created_at")

    all_matches = Match.objects.select_related(
        "lost_item", "found_item", "lost_item__user", "found_item__user"
    ).order_by("-created_at")

    context = {
        "users": users,
        "lost_items": lost_items,
        "found_items": found_items,
        "all_matches": all_matches,
        "total_users": users.count(),
        "total_lost": lost_items.count(),
        "total_found": found_items.count(),
        "total_matches": all_matches.count(),
    }

    return render(request, "items/admin_dashboard.html", context)

@login_required
@require_POST
def update_live_location(request, item_id):

    item = get_object_or_404(
        Item,
        id=item_id,
        user=request.user,
        item_type="FOUND"
    )

    try:
        data = json.loads(request.body)

        latitude = float(data.get("latitude"))
        longitude = float(data.get("longitude"))

        # Validate GPS coordinates
        if not (-90 <= latitude <= 90):
            return JsonResponse(
                {"error": "Invalid latitude"},
                status=400
            )

        if not (-180 <= longitude <= 180):
            return JsonResponse(
                {"error": "Invalid longitude"},
                status=400
            )

        # Save the latest location
        item.current_latitude = latitude
        item.current_longitude = longitude
        item.is_location_sharing = True
        item.location_updated_at = timezone.now()

        item.save(update_fields=[
            "current_latitude",
            "current_longitude",
            "is_location_sharing",
            "location_updated_at"
        ])

        return JsonResponse({
            "success": True,
            "message": "Location updated successfully"
        })

    except (ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse(
            {"error": "Invalid location data"},
            status=400
        )
        

@login_required
@require_POST
def stop_live_location(request, item_id):

    item = get_object_or_404(
        Item,
        id=item_id,
        user=request.user,
        item_type="FOUND"
    )

    item.is_location_sharing = False

    item.save(update_fields=[
        "is_location_sharing"
    ])

    return JsonResponse({
        "success": True,
        "message": "Location sharing stopped"
    })


@login_required
def get_live_location(request, match_id):

    match = get_object_or_404(
        Match,
        id=match_id,
        status="CONFIRMED",
        lost_item__user=request.user
    )

    item = match.found_item

    return JsonResponse({
        "sharing": item.is_location_sharing,
        "latitude": item.current_latitude,
        "longitude": item.current_longitude,
        "updated_at": (
            item.location_updated_at.isoformat()
            if item.location_updated_at else None
        )
    })