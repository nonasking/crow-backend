from django.urls import path

from receivers.views.sms_receiver_view import SMSReceiverView

app_name = "receivers"

urlpatterns = [
    path("webhook/", SMSReceiverView.as_view(), name="webhook"),
]
