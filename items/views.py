
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.views.decorators.http import require_POST
from django.core.mail import send_mail
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q
from django.db import transaction

from .models import Item, Match
from .forms import RegisterForm, ItemForm, EditProfileForm
from .ai.image_matcher import get_image_embedding
from .matching_service import find_matching_items

import json

import logging
from django.core.mail import send_mail

from django.contrib import messages
from django.core.paginator import Paginator



from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash

from django.views.decorators.http import require_POST
from django.core.files.storage import default_storage

# Home page
def home(request):
    return render(request, "items/home.html")


# Browse and search all open items

def browse_items(request):

    search_query = request.GET.get("q", "").strip()

    items = Item.objects.filter(status="OPEN")

    if search_query:

        search_filter = (
            Q(item_name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(location__icontains=search_query)
        )

        if request.user.is_authenticated:
            search_filter |= Q(
                item_code__icontains=search_query,
                user=request.user
            )

        items = items.filter(search_filter)

    items = items.order_by("-created_at")

    paginator = Paginator(items, 10)

    page_number = request.GET.get("page")

    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "items/browse_items.html",
        {
            "items": page_obj,
            "page_obj": page_obj,
            "search_query": search_query
        }
    )


# Display individual item details securely
@login_required
def item_details(request, item_id):

    item = get_object_or_404(Item, id=item_id)

    # Only the item owner can view the private item code
    can_view_item_code = (item.user_id == request.user.id)

    context = {
        "item": item,
        "can_view_item_code": can_view_item_code,
    }

    return render(
        request,
        "items/item_details.html",
        context
    )




@user_passes_test(lambda user: user.is_staff, login_url="login")
def admin_item_details(request, item_id):

    item = get_object_or_404(
        Item.objects.select_related("user"),
        id=item_id
    )

    related_matches = Match.objects.filter(
        Q(lost_item=item) | Q(found_item=item)
    ).select_related(
        "lost_item",
        "found_item",
        "lost_item__user",
        "found_item__user"
    ).order_by("-created_at")

    context = {
        "item": item,
        "related_matches": related_matches,
    }

    return render(
        request,
        "items/admin_item_details.html",
        context
    )


# Register a new user

def register(request):

    if request.method == "POST":

        form = RegisterForm(request.POST)

        if form.is_valid():

            user = form.save()

            login(request, user)

            messages.success(
                request,
                "Your account has been created successfully!"
            )

            return redirect("dashboard")

        else:

            messages.error(
                request,
                "Please correct the errors below."
            )

    else:

        form = RegisterForm()

    return render(
        request,
        "items/register.html",
        {"form": form}
    )


# Report a lost or found item

# Report a lost or found item
@login_required
def report_item(request):

    if request.method == "POST":

        form = ItemForm(request.POST, request.FILES)

        if form.is_valid():

            # Save reported item
            item = form.save(commit=False)
            item.user = request.user
            item.save()

            messages.success(
                request,
                "Your item has been reported successfully!"
            )

            try:
                # Generate image embedding
                embedding = get_image_embedding(item.image.path)

                item.image_embedding = embedding.squeeze().tolist()
                item.save(update_fields=["image_embedding"])

                # Find similar items
                possible_matches = find_matching_items(item)

                # Process every possible match
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

                    # Generate a code for the lost item
                    if not lost_item.item_code:
                        lost_item.save()

                    # Assign the same code to the found item
                    if lost_item.item_code and not found_item.item_code:
                        found_item.item_code = lost_item.item_code
                        found_item.save(update_fields=["item_code"])

                    # Create match in database
                    match, created = Match.objects.get_or_create(
                        lost_item=lost_item,
                        found_item=found_item,
                        defaults={
                            "similarity_score": similarity,
                            "status": "PENDING",
                        },
                    )

                    # Send email only for a newly created match
                    if created and lost_item.user.email:

                        subject = "Possible Match Found - Lost and Found System"

                        message = f"""
Hello {lost_item.user.username},

Good news! We found a possible match for your lost item.

LOST ITEM DETAILS:
Item: {lost_item.item_name}
Your Item Code: {lost_item.item_code}
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

                            print(
                                "Match notification email sent successfully."
                            )

                        except Exception:
                            import logging
                            logging.exception(
                                "Email notification failed."
                            )

            except Exception:
                import logging
                logging.exception(
                    "Image embedding or matching failed for item ID %s",
                    item.pk
                )

            # Redirect found reporters to location sharing
            if item.item_type == "FOUND":
                return redirect("share_location", item_id=item.id)

            return redirect("my_reports")

    else:
        # Create an empty form for GET requests
        form = ItemForm()

    # Display the form (also displays validation errors for invalid POST)
    return render(
        request,
        "items/report_item.html",
        {"form": form}
    )



# Location sharing page
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


# Display logged-in user's reports
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


# Display possible matches
@login_required
def matches(request):
    my_items = Item.objects.filter(user=request.user)

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


# Display dashboard
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





# Confirm a possible match safely

@login_required
@require_POST
@transaction.atomic
def confirm_match(request, match_id):

    match = get_object_or_404(
        Match.objects.select_for_update(),
        id=match_id,
        lost_item__user=request.user,
        status="PENDING"
    )

    lost_item = Item.objects.select_for_update().get(
        id=match.lost_item_id
    )

    found_item = Item.objects.select_for_update().get(
        id=match.found_item_id
    )

    if lost_item.status != "OPEN" or found_item.status != "OPEN":

        match.status = "REJECTED"
        match.save(update_fields=["status"])

        messages.warning(
            request,
            "This item has already been matched or resolved."
        )

        return redirect("matches")

    # Confirm the match
    match.status = "CONFIRMED"
    match.save(update_fields=["status"])

    lost_item.status = "MATCHED"
    lost_item.save(update_fields=["status"])

    found_item.status = "MATCHED"
    found_item.save(update_fields=["status"])

    # Reject other pending matches
    Match.objects.filter(
        status="PENDING"
    ).filter(
        Q(lost_item=lost_item) |
        Q(found_item=found_item)
    ).exclude(
        id=match.id
    ).update(status="REJECTED")

    # Send emails only after the database transaction commits
    def send_confirmation_emails():

        lost_user = lost_item.user
        found_user = found_item.user

        lost_name = lost_user.get_full_name() or lost_user.username
        found_name = found_user.get_full_name() or found_user.username

        # Email to the lost-item owner
        if lost_user.email:
            try:
                send_mail(
                    subject="Thank You for Using Lost and Found!",
                    message=f"""
Hello {lost_name},

Great news! Your lost item, "{lost_item.item_name}",
has been successfully matched with a found item.

Thank you for using our AI-Based Lost and Found
Management System.

We hope you have successfully recovered your belonging.

Thank you for trusting our website!

Regards,
Lost and Found Team
""",
                    from_email=None,
                    recipient_list=[lost_user.email],
                    fail_silently=False
                )
            except Exception:
                logging.exception("Failed to send thank-you email to lost user.")

        # Email to the found-item reporter
        if found_user.email:
            try:
                send_mail(
                    subject="Thank You for Helping Someone!",
                    message=f"""
Hello {found_name},

Thank you for reporting the found item,
"{found_item.item_name}".

Your honesty and kindness helped someone recover
their lost belonging.

The lost-item owner has confirmed the match.

We truly appreciate your contribution to our
AI-Based Lost and Found Management System.

Thank you for making a difference!

Regards,
Lost and Found Team
""",
                    from_email=None,
                    recipient_list=[found_user.email],
                    fail_silently=False
                )
            except Exception:
                logging.exception("Failed to send thank-you email to found user.")

    transaction.on_commit(send_confirmation_emails)

    messages.success(
        request,
        "Match confirmed successfully! Thank-you emails will be sent to both users."
    )

    return redirect("matches")




# Mark an item as successfully found
@login_required
@require_POST
@transaction.atomic
def mark_item_found(request, match_id):

    match = get_object_or_404(
        Match.objects.select_for_update(),
        id=match_id,
        lost_item__user=request.user,
        status="CONFIRMED"
    )

    lost_item = Item.objects.select_for_update().get(
        id=match.lost_item_id
    )

    found_item = Item.objects.select_for_update().get(
        id=match.found_item_id
    )

    # Prevent restarting the countdown
    if lost_item.resolved_at or found_item.resolved_at:
        return redirect("matches")

    now = timezone.now()

    # Resolve both items together
    lost_item.status = "RESOLVED"
    lost_item.resolved_at = now

    found_item.status = "RESOLVED"
    found_item.resolved_at = now

    lost_item.save(
        update_fields=["status", "resolved_at"]
    )

    found_item.save(
        update_fields=["status", "resolved_at"]
    )

    return redirect("matches")



# Reject a possible match

@login_required
@require_POST
def reject_match(request, match_id):

    match = get_object_or_404(
        Match,
        id=match_id,
        lost_item__user=request.user,
        status="PENDING"
    )

    match.status = "REJECTED"
    match.save(update_fields=["status"])

    messages.info(
        request,
        "The possible match has been rejected."
    )

    return redirect("matches")



# Admin dashboard
@user_passes_test(lambda user: user.is_staff, login_url="login")
def admin_dashboard(request):

    users = User.objects.all().order_by("-date_joined")

    lost_items = Item.objects.filter(
        item_type="LOST"
    ).order_by("-created_at")

    found_items = Item.objects.filter(
        item_type="FOUND"
    ).order_by("-created_at")

    all_matches = Match.objects.select_related(
        "lost_item",
        "found_item",
        "lost_item__user",
        "found_item__user"
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

    return render(
        request,
        "items/admin_dashboard.html",
        context
    )
    
    
@user_passes_test(lambda user: user.is_staff, login_url="login")
@require_POST
def admin_delete_item(request, item_id):

    item = get_object_or_404(Item, id=item_id)

    image_name = item.image.name if item.image else None
    image_storage = item.image.storage if item.image else None

    item.delete()

    if image_name:
        image_storage.delete(image_name)

    messages.success(request, "Item deleted successfully!")

    return redirect("admin_dashboard")


@user_passes_test(lambda user: user.is_staff, login_url="login")
@require_POST
def admin_delete_user(request, user_id):

    target_user = get_object_or_404(User, id=user_id)

    if target_user.id == request.user.id:
        messages.error(request, "You cannot delete your own account here.")
        return redirect("admin_dashboard")

    if target_user.is_superuser:
        messages.error(request, "Superuser accounts cannot be deleted here.")
        return redirect("admin_dashboard")

    # Collect images belonging to this user's reported items
    images = [
        (item.image.storage, item.image.name)
        for item in Item.objects.filter(user=target_user).exclude(image="")
    ]

    target_user.delete()

    # Delete the associated image files
    for storage, image_name in images:
        storage.delete(image_name)

    messages.success(request, "User and their reported items deleted successfully!")

    return redirect("admin_dashboard")



@login_required
@require_POST
def update_live_location(request, item_id):

    match = get_object_or_404(
        Match,
        found_item_id=item_id,
        found_item__user=request.user,
        status="CONFIRMED"
    )

    found_item = match.found_item

    try:
        data = json.loads(request.body)

        latitude = float(data.get("latitude"))
        longitude = float(data.get("longitude"))

        if not (-90 <= latitude <= 90):
            raise ValueError("Invalid latitude")

        if not (-180 <= longitude <= 180):
            raise ValueError("Invalid longitude")

    except (ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse({
            "success": False,
            "message": "Invalid location coordinates."
        }, status=400)

    found_item.current_latitude = latitude
    found_item.current_longitude = longitude
    found_item.is_location_sharing = True
    found_item.location_updated_at = timezone.now()

    found_item.save(update_fields=[
        "current_latitude",
        "current_longitude",
        "is_location_sharing",
        "location_updated_at"
    ])

    return JsonResponse({
        "success": True,
        "message": "Location updated successfully."
    })



# Stop live location sharing


@login_required
@require_POST
def stop_live_location(request, match_id):

    match = get_object_or_404(
        Match,
        id=match_id,
        found_item__user=request.user,
        status="CONFIRMED"
    )

    found_item = match.found_item

    found_item.is_location_sharing = False
    found_item.current_latitude = None
    found_item.current_longitude = None
    found_item.location_updated_at = None

    found_item.save(update_fields=[
        "is_location_sharing",
        "current_latitude",
        "current_longitude",
        "location_updated_at"
    ])

    return JsonResponse({
        "success": True,
        "message": "Location sharing stopped and saved coordinates cleared."
    })


@login_required
def get_live_location(request, match_id):

    match = get_object_or_404(
        Match,
        id=match_id,
        lost_item__user=request.user,
        status="CONFIRMED"
    )

    found_item = match.found_item

    if not found_item.is_location_sharing:
        return JsonResponse({
            "success": False,
            "message": "Location sharing is currently unavailable."
        })

    if (
        found_item.current_latitude is None
        or found_item.current_longitude is None
    ):
        return JsonResponse({
            "success": False,
            "message": "Location has not been shared yet."
        })

    return JsonResponse({
        "success": True,
        "latitude": found_item.current_latitude,
        "longitude": found_item.current_longitude,
        "updated_at": (
            found_item.location_updated_at.isoformat()
            if found_item.location_updated_at
            else None
        )
    })
    
    

# User Profile
@login_required
def profile(request):

    user = request.user

    total_lost_items = Item.objects.filter(
        user=user,
        item_type="LOST"
    ).count()

    total_found_items = Item.objects.filter(
        user=user,
        item_type="FOUND"
    ).count()

    total_confirmed_matches = Match.objects.filter(
        Q(lost_item__user=user) |
        Q(found_item__user=user),
        status="CONFIRMED"
    ).count()

    context = {
        "profile_user": user,
        "total_lost_items": total_lost_items,
        "total_found_items": total_found_items,
        "total_confirmed_matches": total_confirmed_matches,
    }

    return render(
        request,
        "items/profile.html",
        context
    )
    
    

# Edit User Profile
@login_required
def edit_profile(request):

    if request.method == "POST":
        form = EditProfileForm(
            request.POST,
            instance=request.user
        )

        if form.is_valid():
            form.save()
            return redirect("profile")

    else:
        form = EditProfileForm(instance=request.user)

    return render(
        request,
        "items/edit_profile.html",
        {"form": form}
    )





# Change User Password
@login_required
def change_password(request):

    if request.method == "POST":
        form = PasswordChangeForm(
            user=request.user,
            data=request.POST
        )

        if form.is_valid():
            user = form.save()

            # Keep the user logged in after changing password
            update_session_auth_hash(request, user)

            return redirect("profile")

    else:
        form = PasswordChangeForm(user=request.user)

    return render(
        request,
        "items/change_password.html",
        {"form": form}
    )

