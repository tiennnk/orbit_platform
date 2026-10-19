from django.urls import path

from apps.assistant.api.views import ChatView

urlpatterns = [
    path("chat/", ChatView.as_view(), name="assistant-chat"),
]
