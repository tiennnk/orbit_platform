from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.assistant.api.serializers import ChatReplySerializer, ChatRequestSerializer
from apps.assistant.services import reply
from apps.shared.serializers import ErrorSerializer


class ChatView(APIView):
    throttle_scope = "assistant"

    @extend_schema(
        tags=["assistant"],
        operation_id="chatWithAssistant",
        request=ChatRequestSerializer,
        responses={200: ChatReplySerializer, 503: ErrorSerializer},
    )
    def post(self, request):
        payload = ChatRequestSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        location = None
        if "latitude" in data:
            location = (data["latitude"], data["longitude"])
        text = reply(user=request.user, history=data["messages"], location=location)
        return Response(ChatReplySerializer({"reply": text}).data)
