from datetime import datetime, timezone, timedelta
from rest_framework import serializers


class GeocodeQuerySerializer(serializers.Serializer):
    q = serializers.CharField(
        min_length=2,
        max_length=200,
        required=True,
        trim_whitespace=True,
        error_messages={
            'required': 'Please enter a location query.',
            'min_length': 'Location query must be at least 2 characters.',
        }
    )


class PlanRequestSerializer(serializers.Serializer):
    origin = serializers.CharField(
        min_length=2,
        max_length=180,
        required=True,
        trim_whitespace=True,
        error_messages={
            'required': 'Origin location is required.',
            'min_length': 'Origin location must be at least 2 characters.',
            'max_length': 'Origin location is too long (maximum 180 characters).',
        }
    )
    destination = serializers.CharField(
        min_length=2,
        max_length=180,
        required=True,
        trim_whitespace=True,
        error_messages={
            'required': 'Destination location is required.',
            'min_length': 'Destination location must be at least 2 characters.',
            'max_length': 'Destination location is too long (maximum 180 characters).',
        }
    )
    departure = serializers.DateTimeField(
        required=True,
        error_messages={
            'required': 'Departure date and time is required.',
            'invalid': 'Invalid departure date/time format. Use standard ISO 8601 (e.g. 2026-10-18T10:00:00Z).',
        }
    )
    load_lbs = serializers.FloatField(
        required=False,
        default=0.0,
        min_value=0.0,
        max_value=100000.0,
        error_messages={
            'min_value': 'Load weight cannot be negative.',
            'max_value': 'Load weight cannot exceed 100,000 lbs for standard commercial vehicles.',
        }
    )
    spacing_miles = serializers.ChoiceField(
        choices=[10, 25, 50],
        default=25,
        error_messages={
            'invalid_choice': 'Checkpoint interval must be 10, 25, or 50 miles.',
        }
    )

    def validate_origin(self, value):
        if value.strip() == '':
            raise serializers.ValidationError("Origin cannot be blank.")
        return value.strip()

    def validate_destination(self, value):
        if value.strip() == '':
            raise serializers.ValidationError("Destination cannot be blank.")
        return value.strip()

    def validate_departure(self, value):
        if value.tzinfo is None:
            raise serializers.ValidationError("Departure timestamp must include timezone information.")
        now = datetime.now(timezone.utc)
        if value < now - timedelta(minutes=30):
            raise serializers.ValidationError("Departure time cannot be in the past.")
        if value > now + timedelta(hours=48):
            raise serializers.ValidationError("Departure must be within the supported 48-hour forecast horizon.")
        return value

