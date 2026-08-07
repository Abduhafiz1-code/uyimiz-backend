"""Profil kengaytmasi (avatar) va SMS-kodlarni vazifasi bo'yicha ajratish.

- ``User.avatar`` — profil rasmi.
- ``PhoneOTP.purpose`` — kirish / telefon almashtirish / shartnoma imzolash uchun
  alohida kodlar. Shu tufayli kirish uchun olingan kod bilan shartnoma imzolab
  bo'lmaydi.
- ``PhoneOTP.attempts`` — noto'g'ri urinishlar soni (brute-force'ga qarshi).
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='avatar',
            field=models.ImageField(blank=True, null=True, upload_to='avatars/'),
        ),
        migrations.AddField(
            model_name='phoneotp',
            name='purpose',
            field=models.CharField(
                choices=[
                    ('login', 'Tizimga kirish'),
                    ('phone_change', "Telefon raqamini o'zgartirish"),
                    ('contract', 'Shartnomani imzolash'),
                ],
                db_index=True,
                default='login',
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name='phoneotp',
            name='reference',
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name='phoneotp',
            name='attempts',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AlterModelOptions(
            name='phoneotp',
            options={'ordering': ['-created_at']},
        ),
    ]
