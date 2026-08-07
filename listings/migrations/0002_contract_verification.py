"""Shartnoma tekshiruvini kuchaytirish.

- Sotuvchi endi avtomatik "rozi" emas (``seller_signed`` default False) va
  alohida tasdiqlash bosqichidan o'tadi (``seller_approved_at``).
- Yangi ``awaiting_sign`` holati: sotuvchi rozi bo'ldi, xaridor imzosi kutilmoqda.
- Bekor qilish sababi va kim bekor qilgani yozib boriladi.
"""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('listings', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='contract',
            name='seller_signed',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='contract',
            name='status',
            field=models.CharField(
                choices=[
                    ('draft', 'Sotuvchi roziligi kutilmoqda'),
                    ('awaiting_sign', 'Imzo kutilmoqda'),
                    ('signed', 'Imzolangan'),
                    ('cancelled', 'Bekor qilingan'),
                ],
                default='draft',
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name='contract',
            name='seller_approved_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='contract',
            name='cancel_reason',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name='contract',
            name='cancelled_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='+',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterModelOptions(
            name='contract',
            options={'ordering': ['-created_at']},
        ),
    ]
