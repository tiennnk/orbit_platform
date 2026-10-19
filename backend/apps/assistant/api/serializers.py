from rest_framework import serializers

MAX_TURNS = 20


class ChatTurnSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=["user", "assistant"])
    content = serializers.CharField(max_length=1000, trim_whitespace=True)


class ChatRequestSerializer(serializers.Serializer):
    messages = ChatTurnSerializer(many=True, max_length=MAX_TURNS, min_length=1)
    latitude = serializers.FloatField(min_value=-90, max_value=90, required=False)
    longitude = serializers.FloatField(min_value=-180, max_value=180, required=False)

    def validate_messages(self, value):
        if value[0]["role"] != "user" or value[-1]["role"] != "user":
            raise serializers.ValidationError(
                "The conversation must start and end with a user message."
            )
        roles = [turn["role"] for turn in value]
        if any(a == b for a, b in zip(roles, roles[1:], strict=False)):
            raise serializers.ValidationError("Roles must alternate.")
        return value

    def validate(self, attrs):
        if ("latitude" in attrs) != ("longitude" in attrs):
            raise serializers.ValidationError("Send latitude and longitude together.")
        return attrs


class ChatReplySerializer(serializers.Serializer):
    reply = serializers.CharField()
