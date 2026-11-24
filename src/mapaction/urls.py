from django.urls import path

from . import views

app_name = "mapaction"

urlpatterns = [
    path("emergencies/", views.emergency_list, name="emergencies"),
    path("emergencies/<str:code>/", views.emergency_detail, name="emergency"),
    path("emergencies/<str:code>/upload/", views.product_upload, name="emergency-upload"),
    path("upload/", views.product_upload, name="upload"),
    path("files/<int:pk>/download", views.file_download, name="file-download"),
]
