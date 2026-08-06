from django.db import models


class District(models.Model):
    """Toshkent tumanlari — 1-bosqich (docx 3-band) shu shahar bilan cheklangan."""

    slug = models.SlugField(max_length=64, unique=True)
    name = models.CharField(max_length=100)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name
