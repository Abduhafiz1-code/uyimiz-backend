"""``python manage.py ensure_admin`` — superadmin hisobini yaratadi yoki parolini yangilaydi.

Render Free tarifida Shell yo'q, shuning uchun admin hisobini qo'lda
yaratib bo'lmaydi. Bu buyruq env o'zgaruvchilardan o'qiydi va konteyner
ishga tushganda avtomatik bajariladi (entrypoint.sh):

    ADMIN_PHONE=+998901234567
    ADMIN_PASSWORD=uzun-parol

Buyruq idempotent: hisob bor bo'lsa faqat parolini yangilaydi, yangi
yozuv yaratmaydi.
"""

import os

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "ADMIN_PHONE / ADMIN_PASSWORD env'laridan superadmin yaratadi"

    def add_arguments(self, parser):
        parser.add_argument('--phone', default=None)
        parser.add_argument('--password', default=None)
        parser.add_argument('--name', default='Superadmin')

    def handle(self, *args, **options):
        from accounts.models import AdminTitle, Role, User, normalize_phone

        phone = options['phone'] or os.environ.get('ADMIN_PHONE', '')
        password = options['password'] or os.environ.get('ADMIN_PASSWORD', '')

        if not phone or not password:
            self.stdout.write(
                'ADMIN_PHONE yoki ADMIN_PASSWORD berilmagan — o\'tkazib yuborildi.'
            )
            return

        if len(password) < 8:
            self.stderr.write("ADMIN_PASSWORD kamida 8 belgidan iborat bo'lsin.")
            return

        phone = normalize_phone(phone)
        if len(phone) < 12:
            self.stderr.write(f"ADMIN_PHONE noto'g'ri: {phone}")
            return

        user, created = User.objects.get_or_create(
            phone=phone,
            defaults={'name': options['name'], 'role': Role.SUPERADMIN},
        )
        user.role = Role.SUPERADMIN
        user.admin_title = AdminTitle.SUPERADMIN
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.verified = True
        user.set_password(password)
        user.save()

        holat = 'yaratildi' if created else 'yangilandi'
        self.stdout.write(self.style.SUCCESS(f'Superadmin {holat}: {phone}'))
