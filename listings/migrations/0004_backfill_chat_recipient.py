"""Mavjud suhbatlarni yangi shaklga moslash.

0003 migratsiyasi ``ChatThread``ga ``recipient`` va ``updated_at``
maydonlarini qo'shdi. Eski qatorlarda ular bo'sh — shu yerda to'ldiramiz:

  * ``recipient`` = e'lon egasi (eski suhbatlar faqat e'lon suhbatlari edi);
  * ``updated_at`` = oxirgi xabar vaqti (chat ro'yxati shu bo'yicha saralanadi).

Migratsiya qaytarilsa (``reverse``) hech narsa qilinmaydi — maydonlar
0003 tomonidan olib tashlanadi.
"""
from django.db import migrations


def backfill(apps, schema_editor):
    ChatThread = apps.get_model('listings', 'ChatThread')
    ChatMessage = apps.get_model('listings', 'ChatMessage')

    threads = ChatThread.objects.filter(listing__isnull=False).select_related('listing')
    for thread in threads.iterator():
        changed = []

        if thread.recipient_id is None:
            thread.recipient_id = thread.listing.owner_id
            changed.append('recipient')

        last = (
            ChatMessage.objects.filter(thread=thread).order_by('-created_at').values_list('created_at', flat=True).first()
        )
        if last:
            thread.updated_at = last
            changed.append('updated_at')

        if changed:
            thread.save(update_fields=changed)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('listings', '0003_alter_chatthread_options_and_more'),
    ]

    operations = [
        migrations.RunPython(backfill, noop),
    ]
