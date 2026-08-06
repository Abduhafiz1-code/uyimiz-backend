from rest_framework import serializers

from .models import Rating


class RatingSerializer(serializers.ModelSerializer):
    rater_name = serializers.CharField(source='rater.name', read_only=True)

    class Meta:
        model = Rating
        fields = [
            'id', 'rater', 'rater_name', 'target_type', 'target_user', 'target_listing',
            'contract', 'score', 'comment', 'created_at',
        ]
        read_only_fields = ['id', 'rater', 'rater_name', 'created_at']

    def validate_score(self, value):
        if not (1 <= value <= 5):
            raise serializers.ValidationError("Baho 1 dan 5 gacha bo'lishi kerak")
        return value
