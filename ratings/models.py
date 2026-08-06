"""docx 2.2-band: "Reyting tizimi: Har bir bitimdan so'ng tomonlar bir-birini
baholaydi". Bitim yopilgach xaridor agentni/e'lon egasini baholaydi.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone


class RatingTarget(models.TextChoices):
    AGENT = 'agent', 'Agent'
    LISTING = 'listing', "E'lon"
    OWNER = 'owner', "E'lon egasi"


class Rating(models.Model):
    rater = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ratings_given')
    target_type = models.CharField(max_length=8, choices=RatingTarget.choices)
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name='ratings_received'
    )
    target_listing = models.ForeignKey(
        'listings.Listing', on_delete=models.CASCADE, null=True, blank=True, related_name='ratings'
    )
    contract = models.ForeignKey(
        'listings.Contract', on_delete=models.SET_NULL, null=True, blank=True, related_name='ratings'
    )
    score = models.PositiveSmallIntegerField()
    comment = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['rater', 'contract', 'target_type'], name='unique_rating_per_contract_target'
            )
        ]

    def __str__(self):
        return f'{self.rater_id} -> {self.target_type} ({self.score})'
