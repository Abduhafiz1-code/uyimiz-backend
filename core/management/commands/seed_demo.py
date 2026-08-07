"""``python manage.py seed_demo`` — uch backend o'rniga bitta demo ma'lumot to'plami.

Yaratadi: tumanlar, superadmin/admin/moderator, bir nechta Uyimiz Agent,
oddiy foydalanuvchilar, e'lonlar (turlicha status/badge bilan), CRM mijoz/
bitim/ko'rsatuv/activity yozuvlari, tariflar va platforma sozlamalari.
"""
import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

DISTRICTS = [
    'Chilonzor', 'Yunusobod', 'Mirzo Ulug\'bek', 'Yakkasaroy', 'Shayxontohur',
    'Mirobod', 'Sergeli', 'Uchtepa', 'Bektemir', 'Yashnobod', 'Olmazor', 'Yangihayot',
]


class Command(BaseCommand):
    help = 'Uyimiz.uz uchun demo ma\'lumotlarni yaratadi'

    def add_arguments(self, parser):
        parser.add_argument('--flush', action='store_true', help='Avval mavjud demo ma\'lumotlarni tozalaydi')

    @transaction.atomic
    def handle(self, *args, **options):
        from accounts.models import AdminTitle, CertificationStatus, Role, User, UserKind
        from core.models import District
        from crm.models import (
            Activity, ActivityKind, Client, ClientStatus, Deal, DealStage, DealType,
            LeadSource, Property, PropertyBadge, PropertyStatus, Showing, ShowingStatus,
        )
        from listings.models import (
            DealKind, DocsState, Listing, ListingBadge, ListingStatus, PropertyType, RepairState,
        )
        from platform_admin.models import PlatformSettings, Tariff

        if options['flush']:
            self.stdout.write('Eski demo ma\'lumotlar tozalanmoqda...')
            User.objects.filter(is_superuser=False).delete()
            Listing.objects.all().delete()
            District.objects.all().delete()
            Tariff.objects.all().delete()

        # ── Tumanlar ──────────────────────────────────────────────
        for i, name in enumerate(DISTRICTS):
            District.objects.get_or_create(slug=name.lower().replace("'", ''), defaults={'name': name, 'order': i})
        self.stdout.write(self.style.SUCCESS(f'{len(DISTRICTS)} ta tuman tayyor'))

        # ── Platforma sozlamalari va tariflar ────────────────────
        PlatformSettings.load()
        tariffs = [
            ('Oddiy e\'lon', 'Bepul', '—', 'Standart joylashtirish'),
            ('Premium e\'lon', "70 000 so'm", 'oy', "Qidiruvda yuqorida chiqadi"),
            ('VIP joylashuv', "200 000 so'm", 'hafta', "Bosh sahifada ko'rinadi"),
            ('Onlayn shartnoma', "50 000 so'm", 'shartnoma', 'PDF + tasdiqlash'),
            ('Uyimiz Agent obunasi', "400 000 so'm", 'oy', 'CRM + avtomatik lead'),
        ]
        for i, (name, price, period, desc) in enumerate(tariffs):
            Tariff.objects.get_or_create(name=name, defaults={
                'price_label': price, 'period': period, 'description': desc, 'order': i
            })
        self.stdout.write(self.style.SUCCESS(f'{len(tariffs)} ta tarif tayyor'))

        # ── Admin panel foydalanuvchilari ────────────────────────
        superadmin, created = User.objects.get_or_create(
            phone='+998900000001',
            defaults=dict(name='Superadmin', role=Role.SUPERADMIN, admin_title=AdminTitle.SUPERADMIN,
                           is_staff=True, is_superuser=True, verified=True),
        )
        if created:
            superadmin.set_password('admin12345')
            superadmin.save()

        admin_user, created = User.objects.get_or_create(
            phone='+998900000002',
            defaults=dict(name='Aziz Karimov', role=Role.ADMIN, admin_title=AdminTitle.ADMIN, verified=True),
        )
        if created:
            admin_user.set_password('admin12345')
            admin_user.save()

        moderator, created = User.objects.get_or_create(
            phone='+998900000003',
            defaults=dict(name='Dilnoza Yusupova', role=Role.ADMIN, admin_title=AdminTitle.MODERATOR, verified=True),
        )
        if created:
            moderator.set_password('admin12345')
            moderator.save()
        self.stdout.write(self.style.SUCCESS('Admin panel akkauntlari: +998900000001/2/3, parol admin12345'))

        # ── Uyimiz Agentlar ───────────────────────────────────────
        agent_names = [
            ('Jasur Toshmatov', 'Chilonzor', 4.8, CertificationStatus.TASDIQLANGAN, 'Top'),
            ('Malika Nazarova', 'Yunusobod', 4.6, CertificationStatus.TASDIQLANGAN, 'Tajribali'),
            ('Bekzod Rashidov', "Mirzo Ulug'bek", 4.2, CertificationStatus.TASDIQLANGAN, 'Faol'),
            ('Nodira Alieva', 'Yakkasaroy', 4.9, CertificationStatus.TASDIQLANGAN, 'Top'),
            ('Sardor Yoldoshev', 'Sergeli', 3.9, CertificationStatus.KUTILMOQDA, 'Yangi'),
        ]
        agents = []
        for i, (name, district, rating, cert, tier) in enumerate(agent_names):
            agent, created = User.objects.get_or_create(
                phone=f'+99890111100{i}',
                defaults=dict(
                    name=name, role=Role.AGENT, district=district, rating=Decimal(str(rating)),
                    rating_count=random.randint(10, 60), certification=cert, tier=tier,
                    verified=True, avg_response_minutes=random.randint(3, 40),
                    historical_deals=random.randint(2, 50), total_deals=random.randint(2, 50),
                ),
            )
            if created:
                agent.set_password('agent12345')
                agent.save()
            agents.append(agent)
        self.stdout.write(self.style.SUCCESS(f'{len(agents)} ta Uyimiz Agent tayyor (parol agent12345)'))

        # ── Oddiy foydalanuvchilar ────────────────────────────────
        user_names = [
            'Otabek Sodiqov', 'Kamola Ergasheva', 'Farrux Islomov', 'Zilola Qodirova',
            'Islom Rahimov', 'Madina Yusupova', 'Sherzod Aliyev', 'Gulnoza Tursunova',
        ]
        users = []
        for i, name in enumerate(user_names):
            # Shartnoma tuzish uchun ikkala tomon ham myID orqali tasdiqlangan
            # bo'lishi shart, shuning uchun demo foydalanuvchilarning aksariyati
            # tasdiqlangan. Oxirgi ikkitasi — tekshiruv to'sig'ini ko'rsatish uchun.
            user, created = User.objects.get_or_create(
                phone=f'+99890222200{i}',
                defaults=dict(
                    name=name,
                    role=Role.USER,
                    user_kind=random.choice(list(UserKind.values)),
                    verified=i < len(user_names) - 2,
                ),
            )
            users.append(user)
        self.stdout.write(self.style.SUCCESS(f'{len(users)} ta oddiy foydalanuvchi tayyor'))

        # ── E'lonlar ──────────────────────────────────────────────
        if not Listing.objects.exists():
            statuses = [ListingStatus.ACTIVE] * 6 + [ListingStatus.PENDING] * 2 + [ListingStatus.REJECTED]
            badges = [ListingBadge.ODDIY] * 6 + [ListingBadge.PREMIUM] * 3 + [ListingBadge.VIP] * 2
            created_count = 0
            for i in range(24):
                owner = random.choice(users)
                by_agent = random.random() < 0.4
                agent = random.choice(agents) if by_agent else None
                district = random.choice(DISTRICTS)
                deal = random.choice(list(DealKind.values))
                price = Decimal(random.randint(25, 220) * 1000) if deal == 'sale' else Decimal(random.randint(200, 1500))
                listing = Listing.objects.create(
                    owner=owner, agent=agent, deal=deal, district=district,
                    address=f'{district} tumani, {random.randint(1, 40)}-uy',
                    price=price, currency='usd' if deal == 'sale' else 'usd',
                    rooms=random.randint(1, 5), area=Decimal(random.randint(30, 180)),
                    floor=random.randint(1, 16), floors=random.randint(4, 18),
                    year=random.randint(1990, 2024),
                    ptype=random.choice(list(PropertyType.values)),
                    repair=random.choice(list(RepairState.values)),
                    # Hujjatlari tayyor bo'lmagan e'longa shartnoma ochilmaydi —
                    # bir nechtasini shu holatda qoldiramiz.
                    docs=DocsState.READY if random.random() < 0.85 else DocsState.PROCESS,
                    verified=random.random() < 0.6,
                    status=random.choice(statuses), badge=random.choice(badges),
                    description='Qulay joylashuvda, barcha qulayliklarga ega uy-joy.',
                    created_at=timezone.now() - timedelta(days=random.randint(0, 20)),
                )
                if listing.badge != ListingBadge.ODDIY:
                    listing.promoted_until = timezone.now() + timedelta(days=14)
                    listing.save(update_fields=['promoted_until'])
                created_count += 1
            self.stdout.write(self.style.SUCCESS(f'{created_count} ta e\'lon yaratildi'))

        # ── CRM demo: mijozlar, obyektlar, bitimlar ─────────────────
        if not Client.objects.exists():
            requests = ['2 xona, Chilonzor', '3 xona, Yunusobod', 'Hovli uy, Sergeli', 'Ofis, Mirzo Ulug\'bek']
            for agent in agents[:3]:
                for j in range(4):
                    client = Client.objects.create(
                        agent=agent, name=random.choice(user_names), phone=f'+99893{random.randint(1000000,9999999)}',
                        request=random.choice(requests), deal_type=random.choice(list(DealType.values)),
                        district=agent.district, budget_label='$50 000 - $90 000',
                        status=random.choice(list(ClientStatus.values)),
                        source=random.choice(list(LeadSource.values)),
                        created_at=timezone.now() - timedelta(days=random.randint(0, 14)),
                    )
                    Activity.objects.create(agent=agent, client=client, kind=ActivityKind.MIJOZ,
                                             text=f'Yangi mijoz qo\'shildi: {client.name}')

                for j in range(3):
                    listing_id = f'UY-{agent.id}{j:03d}'
                    prop = Property.objects.create(
                        agent=agent, listing_id=listing_id, title=f'{random.choice(["2","3","4"])} xonali kvartira',
                        district=agent.district, address=f'{agent.district}, {random.randint(1,50)}-uy',
                        deal_type=random.choice(list(DealType.values)),
                        price=Decimal(random.randint(40, 180) * 1000), currency='USD',
                        rooms=random.randint(1, 5), area=Decimal(random.randint(35, 150)),
                        floor=random.randint(1, 12), total_floors=random.randint(5, 16),
                        built_year=random.randint(2000, 2024),
                        status=random.choice(list(PropertyStatus.values)),
                        badge=random.choice(list(PropertyBadge.values)),
                    )
                    if random.random() < 0.5:
                        client = agent.clients.order_by('?').first()
                        if client:
                            deal = Deal.objects.create(
                                agent=agent, client=client, listing=prop,
                                stage=random.choice(list(DealStage.values)),
                                amount=prop.price, currency=prop.currency,
                                commission=(prop.price * agent.commission_rate / 100).quantize(Decimal('1')),
                            )
                            if deal.stage == DealStage.YOPILGAN:
                                deal.platform_cut = (deal.commission * agent.platform_share / 100).quantize(Decimal('1'))
                                deal.closed_at = timezone.now() - timedelta(days=random.randint(0, 10))
                                deal.contract_signed = True
                                deal.save()
                            Showing.objects.create(
                                agent=agent, client=client, listing=prop,
                                scheduled_at=timezone.now() + timedelta(days=random.randint(1, 7)),
                                status=random.choice(list(ShowingStatus.values)),
                            )
                agent.recalc_tier()
            self.stdout.write(self.style.SUCCESS('CRM demo ma\'lumotlari yaratildi'))

        self.stdout.write(self.style.SUCCESS('\nDemo ma\'lumotlar tayyor!'))
        self.stdout.write('Superadmin:  +998900000001 / admin12345')
        self.stdout.write('Admin:       +998900000002 / admin12345')
        self.stdout.write('Moderator:   +998900000003 / admin12345')
        self.stdout.write('Agent:       +998901111000 / agent12345')
        self.stdout.write('Oddiy user:  +998902222000 (SMS-kod orqali, /api/auth/send-code)')
