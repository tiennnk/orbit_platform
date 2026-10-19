from rest_framework import serializers


class PlaceSearchQuerySerializer(serializers.Serializer):
    q = serializers.CharField(min_length=2, max_length=200)
    latitude = serializers.FloatField(min_value=-90, max_value=90, required=False)
    longitude = serializers.FloatField(min_value=-180, max_value=180, required=False)

    def validate(self, attrs):
        if ("latitude" in attrs) != ("longitude" in attrs):
            raise serializers.ValidationError("Send latitude and longitude together.")
        return attrs


class PlaceSerializer(serializers.Serializer):
    name = serializers.CharField()
    address = serializers.CharField()
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
