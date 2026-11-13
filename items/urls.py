from django.urls import path


from django.contrib.auth import views as auth_views


from . import views


urlpatterns = [
    path("", views.home, name="home"),

    path("items/", views.browse_items, name="browse_items"),

    path("report/", views.report_item, name="report_item"),

    path("my-reports/", views.my_reports, name="my_reports"),

    path("matches/", views.matches, name="matches"),

    path("register/", views.register, name="register"),
 
    path("dashboard/", views.dashboard, name="dashboard"),
    
    path("matches/", views.matches, name="matches"),
    
    path("match/<int:match_id>/confirm/", views.confirm_match, name="confirm_match"),
    
    path("match/<int:match_id>/reject/", views.reject_match, name="reject_match"),
 
    path("admin_dashboard/", views.admin_dashboard, name="admin_dashboard"),
    
    path("share-location/<int:item_id>/",views.share_location,name="share_location"),
  
    path(
    "update-location/<int:item_id>/",
    views.update_live_location,
    name="update_live_location"
    ),

    path(
        "stop-location/<int:item_id>/",
        views.stop_live_location,
        name="stop_live_location"
    ),

    path(
        "live-location/<int:match_id>/",
        views.get_live_location,
        name="get_live_location"
    ),
    
    path(
    "item-details/<int:item_id>/",
    views.item_details,
    name="item_details"
),
    
    path(
    "mark-item-found/<int:match_id>/",
    views.mark_item_found,
    name="mark_item_found"
),
    
path("profile/", views.profile, name="profile"),



path("edit-profile/", views.edit_profile, name="edit_profile"),
 
 
 
path(
    "change-password/",
    views.change_password,
    name="change_password"
),



path(
    "forgot-password/",
    auth_views.PasswordResetView.as_view(
        template_name="items/forgot_password.html",
        email_template_name="items/password_reset_email.html",
        subject_template_name="items/password_reset_subject.txt",
        success_url="/reset-email-sent/"
    ),
    name="password_reset"
),

path(
    "reset-email-sent/",
    auth_views.PasswordResetDoneView.as_view(
        template_name="items/password_reset_done.html"
    ),
    name="password_reset_done"
),

path(
    "reset/<uidb64>/<token>/",
    auth_views.PasswordResetConfirmView.as_view(
        template_name="items/password_reset_confirm.html",
        success_url="/password-reset-complete/"
    ),
    name="password_reset_confirm"
),

path(
    "password-reset-complete/",
    auth_views.PasswordResetCompleteView.as_view(
        template_name="items/password_reset_complete.html"
    ),
    name="password_reset_complete"
),

path(
    "admin-dashboard/delete-item/<int:item_id>/",
    views.admin_delete_item,
    name="admin_delete_item"
),

path(
    "admin-dashboard/delete-user/<int:user_id>/",
    views.admin_delete_user,
    name="admin_delete_user"
),


path(
    "admin-dashboard/item/<int:item_id>/",
    views.admin_item_details,
    name="admin_item_details"
),    
]