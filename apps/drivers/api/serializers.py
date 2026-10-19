from rest_framework import serializers

from apps.drivers.models import Driver


class DriverCreateSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=255)
    phone = serializers.CharField(max_length=20)


class DriverSerializer(serializers.ModelSerializer):
    class Meta:
        model = Driver
        fields = [
            "id",
            "full_name",
            "phone",
            "approval_status",
            "is_online",
            "availability",
            "created_at",
        ]
        read_only_fields = fields
