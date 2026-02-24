from django.urls import path
from rest_framework.routers import DefaultRouter

from receivers.views.sms_receiver_view import SMSReceiverView

router = DefaultRouter()

app_name = "receivers"

urlpatterns = [
    path("webhook/", SMSReceiverView.as_view(), name="webhook"),
]
