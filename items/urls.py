from django.urls import path

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
    
    
 ]