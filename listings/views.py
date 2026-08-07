from decimal import Decimal, InvalidOperation

from django.db.models import Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from .models import (
    ChatMessage,
    ChatThread,
    Contract,
    ContractStatus,
    DocsState,
    Favorite,
    Listing,
    ListingStatus,
)
from .pdf import render_contract_pdf
from .serializers import (
    ChatMessageSerializer,
    ChatThreadSerializer,
    ContractSerializer,
    ListingPhotoSerializer,
    ListingSerializer,
)


class ListingPagination(PageNumberPagination):
    page_size = 12
    page_size_query_param = 'perPage'
    max_page_size = 50
    page_query_param = 'page'

    def get_paginated_response(self, data):
        return Response({
            'items': data,
            'total': self.page.paginator.count,
            'page': self.page.number,
            'perPage': self.get_page_size(self.request),
            'pageCount': self.page.paginator.num_pages,
        })


class ListingViewSet(viewsets.ModelViewSet):
    """2.2-band: e'lon joylash + qidiruv tizimi (shahar, narx, xona, tur, holat)."""

    serializer_class = ListingSerializer
    pagination_class = ListingPagination
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        if self.action in ('create',):
            return [IsAuthenticated()]
        if self.action in ('update', 'partial_update', 'destroy', 'upload_photos', 'delete_photo', 'mine'):
            return [IsAuthenticated()]
        return [AllowAny()]

    def get_queryset(self):
        qs = Listing.objects.select_related('owner', 'agent').prefetch_related('photos')
        user = self.request.user
        if self.action in ('list',) and not (user.is_authenticated and user.role in ('admin', 'superadmin')):
            qs = qs.filter(status__in=[ListingStatus.ACTIVE, ListingStatus.PENDING])
        q = self.request.query_params
        if deal := q.get('deal'):
            qs = qs.filter(deal=deal)
        if district := q.get('district'):
            qs = qs.filter(district=district)
        if rooms := q.get('rooms'):
            try:
                rooms = int(rooms)
                qs = qs.filter(rooms__gte=4) if rooms >= 4 else qs.filter(rooms=rooms)
            except ValueError:
                pass
        if price_min := q.get('priceMin'):
            qs = qs.filter(price__gte=_dec(price_min))
        if price_max := q.get('priceMax'):
            qs = qs.filter(price__lte=_dec(price_max))
        if q.get('verified') == '1':
            qs = qs.filter(verified=True)
        if q.get('ownerOnly') == '1':
            qs = qs.filter(agent__isnull=True)
        if search := q.get('q'):
            qs = qs.filter(Q(district__icontains=search) | Q(address__icontains=search))

        sort = q.get('sort', 'new')
        order = {
            'cheap': ['price'],
            'expensive': ['-price'],
            'area': ['-area'],
        }.get(sort, ['-created_at'])
        # "Top e'lon"/Premium joylashuv har doim ustunlik oladi (docx 3-bosqich, 2-band).
        qs = qs.order_by('-badge', *order)
        return qs

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        favs = set()
        if request.user.is_authenticated:
            favs = set(Favorite.objects.filter(user=request.user).values_list('listing_id', flat=True))
        for item in response.data.get('items', []):
            item['is_favorite'] = item['id'] in favs
        return response

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        Listing.objects.filter(pk=instance.pk).update(views=instance.views + 1)
        instance.refresh_from_db(fields=['views'])
        serializer = self.get_serializer(instance)
        return Response({'listing': serializer.data})

    def perform_create(self, serializer):
        user = self.request.user
        agent = user if user.role == 'agent' else None
        serializer.save(
            owner=user,
            agent=agent,
            verified=user.verified,
            status=ListingStatus.PENDING,
        )

    def perform_update(self, serializer):
        listing = self.get_object()
        if listing.owner_id != self.request.user.id and listing.agent_id != self.request.user.id:
            raise PermissionError("Bu e'lon sizga tegishli emas")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.owner_id != self.request.user.id and instance.agent_id != self.request.user.id:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Bu e'lon sizga tegishli emas")
        instance.delete()

    @action(detail=False, methods=['get'], url_path='mine')
    def mine(self, request):
        qs = Listing.objects.filter(Q(owner=request.user) | Q(agent=request.user)).prefetch_related('photos')
        page = self.paginate_queryset(qs)
        serializer = self.get_serializer(page or qs, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response({'items': serializer.data})

    @action(detail=True, methods=['post'], url_path='photos')
    def upload_photos(self, request, pk=None):
        listing = self.get_object()
        if listing.owner_id != request.user.id and listing.agent_id != request.user.id:
            return Response({'detail': "Bu e'lon sizga tegishli emas"}, status=status.HTTP_403_FORBIDDEN)
        files = request.FILES.getlist('images') or request.FILES.getlist('image')
        if not files:
            return Response({'detail': 'Rasm yuborilmadi'}, status=status.HTTP_400_BAD_REQUEST)
        start = listing.photos.count()
        created = []
        for i, f in enumerate(files):
            serializer = ListingPhotoSerializer(data={'image': f, 'order': start + i})
            serializer.is_valid(raise_exception=True)
            created.append(serializer.save(listing=listing))
        return Response(
            ListingPhotoSerializer(created, many=True, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['delete'], url_path='photos/(?P<photo_id>[^/.]+)')
    def delete_photo(self, request, pk=None, photo_id=None):
        listing = self.get_object()
        photo = listing.photos.filter(pk=photo_id).first()
        if photo is None:
            return Response({'detail': 'Rasm topilmadi'}, status=status.HTTP_404_NOT_FOUND)
        photo.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


def _dec(value):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError):
        return Decimal('0')


# ───────────────────────── sevimlilar ─────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def favorites_view(request):
    ids = Favorite.objects.filter(user=request.user).values_list('listing_id', flat=True)
    items = Listing.objects.filter(id__in=ids).prefetch_related('photos')
    serializer = ListingSerializer(items, many=True, context={'request': request, 'favorite_ids': set(ids)})
    return Response({'items': serializer.data})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def favorite_toggle_view(request, pk):
    listing = Listing.objects.filter(pk=pk).first()
    if not listing:
        return Response({'error': 'not_found'}, status=status.HTTP_404_NOT_FOUND)
    fav = Favorite.objects.filter(user=request.user, listing=listing).first()
    if fav:
        fav.delete()
        added = False
    else:
        Favorite.objects.create(user=request.user, listing=listing)
        added = True
    ids = list(Favorite.objects.filter(user=request.user).values_list('listing_id', flat=True))
    return Response({'added': added, 'favorites': ids})


# ───────────────────────── chat ─────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def listing_chat_view(request, pk):
    """Xaridor ↔ e'lon egasi suhbati. Kim yozsa ham shu ikkovi orasidagi thread ishlaydi."""
    listing = Listing.objects.filter(pk=pk).first()
    if not listing:
        return Response({'error': 'not_found'}, status=status.HTTP_404_NOT_FOUND)

    user = request.user
    buyer = listing.owner if user.id == listing.owner_id else user
    # Agar egasi o'zi ochsa va query orqali buyer ko'rsatilmasa — barcha threadlar ro'yxati qaytadi.
    if user.id == listing.owner_id and not request.query_params.get('with'):
        threads = ChatThread.objects.filter(listing=listing).select_related('buyer')
        return Response({'items': ChatThreadSerializer(threads, many=True).data})

    if user.id == listing.owner_id:
        from accounts.models import User
        buyer = User.objects.filter(pk=request.query_params.get('with')).first()
        if not buyer:
            return Response({'error': 'buyer_not_found'}, status=status.HTTP_404_NOT_FOUND)

    thread, _ = ChatThread.objects.get_or_create(listing=listing, buyer=buyer)

    if request.method == 'POST':
        text = str(request.data.get('text', '')).strip()
        if not text:
            return Response({'error': 'empty_text'}, status=status.HTTP_400_BAD_REQUEST)
        ChatMessage.objects.create(thread=thread, sender=user, text=text)

    items = ChatMessage.objects.filter(thread=thread).select_related('sender')
    return Response({'items': ChatMessageSerializer(items, many=True).data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_chats_view(request):
    threads = ChatThread.objects.filter(
        Q(buyer=request.user) | Q(listing__owner=request.user)
    ).select_related('listing', 'buyer').distinct()
    return Response({'items': ChatThreadSerializer(threads, many=True).data})


# ───────────────────────── shartnoma ─────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_contract_view(request, pk):
    """Shartnoma so'rovi. Bu yerda "uy oldi-berdi" tekshiruvining asosiy qismi bajariladi.

    Shartlar (docx 2.2-band, "Onlayn shartnoma" + "Verifikatsiya"):
      1. E'lon mavjud va o'zinikiga shartnoma tuzilmaydi;
      2. E'lon FAOL holatda (moderatsiyadan o'tgan, rad etilmagan, sotilmagan);
      3. E'lon hujjatlari tayyor;
      4. Xaridor ham, sotuvchi ham myID/SMS orqali tasdiqlangan;
      5. Shu e'lon bo'yicha ochiq shartnoma allaqachon mavjud emas.
    """
    listing = Listing.objects.select_related('owner').filter(pk=pk).first()
    if not listing:
        return Response({'error': 'not_found'}, status=status.HTTP_404_NOT_FOUND)

    buyer = request.user
    if listing.owner_id == buyer.id:
        return Response({'error': 'own_listing'}, status=status.HTTP_400_BAD_REQUEST)

    if listing.status != ListingStatus.ACTIVE:
        code = 'listing_dealt' if listing.status == ListingStatus.DEALT else 'listing_not_active'
        return Response({'error': code}, status=status.HTTP_400_BAD_REQUEST)

    if listing.docs != DocsState.READY:
        return Response({'error': 'docs_not_ready'}, status=status.HTTP_400_BAD_REQUEST)

    if not buyer.verified:
        return Response({'error': 'buyer_not_verified'}, status=status.HTTP_403_FORBIDDEN)
    if not listing.owner.verified:
        return Response({'error': 'seller_not_verified'}, status=status.HTTP_400_BAD_REQUEST)

    existing = Contract.objects.filter(
        listing=listing, status__in=[ContractStatus.DRAFT, ContractStatus.AWAITING_SIGN]
    ).first()
    if existing:
        if existing.buyer_id == buyer.id:
            # O'zining ochiq shartnomasi — yangisini yaratmay, borini qaytaramiz.
            return Response(ContractSerializer(existing, context={'request': request}).data)
        return Response({'error': 'contract_in_progress'}, status=status.HTTP_409_CONFLICT)

    if Contract.objects.filter(listing=listing, status=ContractStatus.SIGNED).exists():
        return Response({'error': 'listing_dealt'}, status=status.HTTP_400_BAD_REQUEST)

    from platform_admin.models import PlatformSettings
    settings_row = PlatformSettings.load()

    contract = Contract.objects.create(
        listing=listing,
        seller=listing.owner,
        buyer=buyer,
        agent=listing.agent,
        deal=listing.deal,
        price=listing.price,
        currency=listing.currency,
        service_fee=settings_row.contract_price,
        status=ContractStatus.DRAFT,
    )
    return Response(
        ContractSerializer(contract, context={'request': request}).data, status=status.HTTP_201_CREATED
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def approve_contract_view(request, pk):
    """Sotuvchi roziligi — shartnoma imzolashga faqat shundan keyin ochiladi."""
    contract = Contract.objects.filter(pk=pk).select_related('listing', 'seller', 'buyer').first()
    if not contract:
        return Response({'error': 'not_found'}, status=status.HTTP_404_NOT_FOUND)
    if contract.seller_id != request.user.id:
        return Response({'error': 'only_seller'}, status=status.HTTP_403_FORBIDDEN)
    if contract.status == ContractStatus.CANCELLED:
        return Response({'error': 'contract_cancelled'}, status=status.HTTP_400_BAD_REQUEST)
    if contract.status != ContractStatus.DRAFT:
        return Response(ContractSerializer(contract, context={'request': request}).data)

    contract.seller_signed = True
    contract.seller_approved_at = timezone.now()
    contract.status = ContractStatus.AWAITING_SIGN
    contract.save(update_fields=['seller_signed', 'seller_approved_at', 'status'])
    return Response(ContractSerializer(contract, context={'request': request}).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_contract_view(request, pk):
    """Ikkala tomon ham bekor qila oladi (imzolangandan keyin — yo'q)."""
    contract = Contract.objects.filter(pk=pk).select_related('listing').first()
    if not contract:
        return Response({'error': 'not_found'}, status=status.HTTP_404_NOT_FOUND)
    if request.user.id not in (contract.seller_id, contract.buyer_id):
        return Response({'error': 'forbidden'}, status=status.HTTP_403_FORBIDDEN)
    if contract.status == ContractStatus.SIGNED:
        return Response({'error': 'already_signed'}, status=status.HTTP_400_BAD_REQUEST)

    contract.status = ContractStatus.CANCELLED
    contract.cancelled_by = request.user
    contract.cancel_reason = str(request.data.get('reason', ''))[:200]
    contract.save(update_fields=['status', 'cancelled_by', 'cancel_reason'])
    return Response(ContractSerializer(contract, context={'request': request}).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def sign_request_view(request, pk):
    """Imzolash uchun xaridor telefoniga bir martalik kod yuboradi."""
    from accounts.models import OTPPurpose
    from accounts.views import OTP_TTL_SECONDS, issue_otp

    contract = Contract.objects.filter(pk=pk).first()
    if not contract:
        return Response({'error': 'not_found'}, status=status.HTTP_404_NOT_FOUND)
    if contract.buyer_id != request.user.id:
        return Response({'error': 'only_buyer'}, status=status.HTTP_403_FORBIDDEN)
    if contract.status == ContractStatus.SIGNED:
        return Response({'error': 'already_signed'}, status=status.HTTP_400_BAD_REQUEST)
    if contract.status == ContractStatus.CANCELLED:
        return Response({'error': 'contract_cancelled'}, status=status.HTTP_400_BAD_REQUEST)
    if not contract.seller_signed:
        return Response({'error': 'seller_not_approved'}, status=status.HTTP_400_BAD_REQUEST)

    otp, cooldown = issue_otp(request.user.phone, OTPPurpose.CONTRACT, reference=contract.id)
    if otp is None:
        return Response(
            {'error': 'too_soon', 'retryAfterSec': cooldown}, status=status.HTTP_429_TOO_MANY_REQUESTS
        )
    return Response({
        'ok': True, 'phone': request.user.phone, 'demoCode': otp.code, 'expiresInSec': OTP_TTL_SECONDS,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def sign_contract_view(request, pk):
    """Imzolash — faqat to'g'ri SMS-kod bilan va faqat sotuvchi roziligidan keyin."""
    from accounts.models import OTPPurpose
    from accounts.views import check_otp

    contract = Contract.objects.filter(pk=pk).select_related('listing', 'seller', 'buyer').first()
    if not contract:
        return Response({'error': 'not_found'}, status=status.HTTP_404_NOT_FOUND)
    if contract.buyer_id != request.user.id:
        return Response({'error': 'only_buyer'}, status=status.HTTP_403_FORBIDDEN)
    if contract.status == ContractStatus.SIGNED:
        return Response(ContractSerializer(contract, context={'request': request}).data)
    if contract.status == ContractStatus.CANCELLED:
        return Response({'error': 'contract_cancelled'}, status=status.HTTP_400_BAD_REQUEST)
    if not contract.seller_signed:
        return Response({'error': 'seller_not_approved'}, status=status.HTTP_400_BAD_REQUEST)
    if not request.user.verified:
        return Response({'error': 'buyer_not_verified'}, status=status.HTTP_403_FORBIDDEN)

    code = request.data.get('code')
    if not code:
        return Response({'error': 'code_required'}, status=status.HTTP_400_BAD_REQUEST)

    ok, error = check_otp(request.user.phone, code, OTPPurpose.CONTRACT, reference=contract.id)
    if not ok:
        return Response({'error': error}, status=status.HTTP_400_BAD_REQUEST)

    contract.buyer_signed = True
    contract.status = ContractStatus.SIGNED
    contract.signed_at = timezone.now()
    render_contract_pdf(contract)
    contract.save()

    contract.listing.status = ListingStatus.DEALT
    contract.listing.save(update_fields=['status'])

    # Shu e'lon bo'yicha boshqa ochiq so'rovlar avtomatik bekor qilinadi.
    Contract.objects.filter(
        listing=contract.listing, status__in=[ContractStatus.DRAFT, ContractStatus.AWAITING_SIGN]
    ).exclude(pk=contract.pk).update(status=ContractStatus.CANCELLED, cancel_reason='Boshqa xaridor bilan bitim yopildi')

    if contract.agent_id:
        _sync_crm_deal(contract)

    return Response(ContractSerializer(contract, context={'request': request}).data)


def _sync_crm_deal(contract):
    """Agent ishtirokidagi bitim CRM pipeline'iga avtomatik tushadi (docx 5-band)."""
    from crm.models import Client, ClientStatus, Deal, DealStage
    from decimal import Decimal as D

    client, _ = Client.objects.get_or_create(
        agent=contract.agent, phone=contract.buyer.phone,
        defaults={
            'name': contract.buyer.name,
            'request': f'{contract.listing.district} — {contract.listing.get_deal_display()}',
            'deal_type': _crm_deal_type(contract.deal),
            'district': contract.listing.district,
            'status': ClientStatus.SHARTNOMADA,
        },
    )
    commission = (contract.price * contract.agent.commission_rate / D('100')).quantize(D('1'))
    platform_cut = (commission * contract.agent.platform_share / D('100')).quantize(D('1'))
    Deal.objects.create(
        agent=contract.agent,
        client=client,
        listing=None,
        stage=DealStage.YOPILGAN,
        amount=contract.price,
        currency=contract.currency.upper(),
        commission=commission,
        platform_cut=platform_cut,
        contract_signed=True,
        closed_at=timezone.now(),
    )
    contract.agent.recalc_tier()


def _crm_deal_type(deal_kind):
    from crm.models import DealType
    return {'sale': DealType.SOTIB_OLISH, 'rent': DealType.IJARA, 'daily': DealType.KUNLIK}.get(
        deal_kind, DealType.SOTIB_OLISH
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def contract_detail_view(request, pk):
    contract = Contract.objects.filter(pk=pk).first()
    if not contract:
        return Response({'error': 'not_found'}, status=status.HTTP_404_NOT_FOUND)
    if request.user.id not in (contract.seller_id, contract.buyer_id) and request.user.role not in (
        'admin', 'superadmin',
    ):
        return Response({'error': 'forbidden'}, status=status.HTTP_403_FORBIDDEN)
    return Response(ContractSerializer(contract, context={'request': request}).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_contracts_view(request):
    items = Contract.objects.filter(Q(seller=request.user) | Q(buyer=request.user)).select_related(
        'listing', 'seller', 'buyer'
    )
    return Response({'items': ContractSerializer(items, many=True, context={'request': request}).data})
