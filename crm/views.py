from datetime import timedelta
from decimal import Decimal

from django.db.models import Avg, Count, Q, Sum
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from accounts.models import Role, TIER_ORDER, TIER_THRESHOLDS, User
from accounts.permissions import IsAgent
from accounts.serializers import AgentSerializer

from .models import (
    CLOSED_CLIENT_STATUSES,
    OPEN_DEAL_STAGES,
    Activity,
    Client,
    Deal,
    DealStage,
    Property,
    Showing,
)
from .serializers import (
    ActivitySerializer,
    ClientSerializer,
    DealSerializer,
    LeadCreateSerializer,
    PropertyPhotoSerializer,
    PropertySerializer,
    ShowingSerializer,
)
from .services import assign_lead


class AgentScopedViewSet(viewsets.ModelViewSet):
    """Har bir CRM yozuvi faqat bitta agentga tegishli — hech qachon oralashmaydi."""

    permission_classes = [IsAgent]

    def get_queryset(self):
        return self.queryset.filter(agent=self.request.user)

    def perform_create(self, serializer):
        serializer.save(agent=self.request.user)


class ClientViewSet(AgentScopedViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        if search := params.get('search'):
            qs = qs.filter(Q(name__icontains=search) | Q(phone__icontains=search) | Q(request__icontains=search))
        if status_filter := params.get('status'):
            qs = qs.filter(status=status_filter)
        if source := params.get('source'):
            qs = qs.filter(source=source)
        if deal_type := params.get('deal_type'):
            qs = qs.filter(deal_type=deal_type)
        if params.get('open') == 'true':
            qs = qs.exclude(status__in=CLOSED_CLIENT_STATUSES)
        return qs


class PropertyViewSet(AgentScopedViewSet):
    queryset = Property.objects.prefetch_related('photos').all()
    serializer_class = PropertySerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        if search := params.get('search'):
            qs = qs.filter(
                Q(title__icontains=search) | Q(address__icontains=search)
                | Q(listing_id__icontains=search) | Q(district__icontains=search)
            )
        if status_filter := params.get('status'):
            qs = qs.filter(status=status_filter)
        if deal_type := params.get('deal_type'):
            qs = qs.filter(deal_type=deal_type)
        if params.get('verified') == 'true':
            qs = qs.filter(is_verified=True)
        return qs

    @action(detail=True, methods=['post'], url_path='photos')
    def upload_photos(self, request, pk=None):
        listing = self.get_object()
        files = request.FILES.getlist('images') or request.FILES.getlist('image')
        if not files:
            return Response({'detail': 'Rasm yuborilmadi'}, status=status.HTTP_400_BAD_REQUEST)
        start = listing.photos.count()
        created = []
        for i, f in enumerate(files):
            serializer = PropertyPhotoSerializer(data={'image': f, 'order': start + i})
            serializer.is_valid(raise_exception=True)
            created.append(serializer.save(listing=listing))
        listing.refresh_from_db()
        return Response(
            PropertyPhotoSerializer(created, many=True, context={'request': request}).data,
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


class DealViewSet(AgentScopedViewSet):
    queryset = Deal.objects.select_related('client', 'listing').all()
    serializer_class = DealSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        if stage := params.get('stage'):
            qs = qs.filter(stage=stage)
        if search := params.get('search'):
            qs = qs.filter(Q(client__name__icontains=search) | Q(listing__title__icontains=search))
        return qs

    def perform_update(self, serializer):
        deal = serializer.save()
        if deal.stage == DealStage.YOPILGAN and deal.closed_at is None:
            deal.closed_at = timezone.now()
            deal.save(update_fields=['closed_at'])
        elif deal.stage != DealStage.YOPILGAN and deal.closed_at is not None:
            deal.closed_at = None
            deal.save(update_fields=['closed_at'])
        self.request.user.recalc_tier()


class ShowingViewSet(AgentScopedViewSet):
    queryset = Showing.objects.select_related('client', 'listing').all()
    serializer_class = ShowingSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get('upcoming') == 'true':
            qs = qs.filter(scheduled_at__gte=timezone.now())
        return qs


class ActivityViewSet(AgentScopedViewSet):
    queryset = Activity.objects.select_related('client').all()
    serializer_class = ActivitySerializer


@api_view(['GET'])
@permission_classes([IsAgent])
def dashboard_view(request):
    agent = request.user
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)

    clients = Client.objects.filter(agent=agent)
    deals = Deal.objects.filter(agent=agent)

    active_clients = clients.exclude(status__in=CLOSED_CLIENT_STATUSES)
    month_deals = deals.filter(stage=DealStage.YOPILGAN, closed_at__gte=month_start)

    commission_total = month_deals.aggregate(total=Sum('commission'))['total'] or Decimal('0')
    platform_total = month_deals.aggregate(total=Sum('platform_cut'))['total'] or Decimal('0')
    platform_percent = round(platform_total / commission_total * 100) if commission_total else agent.platform_share

    new_clients = list(active_clients.filter(created_at__gte=week_ago).order_by('-created_at')[:6])
    if not new_clients:
        new_clients = list(active_clients.order_by('-created_at')[:6])

    percent, remaining, next_label = agent.tier_progress()

    return Response({
        'agent': AgentSerializer(agent).data,
        'greeting_note': _greeting_note(clients, week_ago),
        'kpi': {
            'active_clients': active_clients.count(),
            'active_clients_delta': clients.filter(created_at__gte=week_ago).count(),
            'month_deals': month_deals.count(),
            'month_deals_delta': deals.filter(stage=DealStage.YOPILGAN, closed_at__gte=week_ago).count(),
            'commission_income': commission_total,
            'platform_share': platform_percent,
            'response_minutes': agent.avg_response_minutes,
        },
        'tier': {
            'percent': percent, 'remaining': remaining, 'next_label': next_label,
            'current': agent.tier, 'rating': agent.rating,
        },
        'new_clients': ClientSerializer(new_clients, many=True).data,
        'pipeline': _pipeline_counts(deals),
        'upcoming_showings': ShowingSerializer(
            Showing.objects.filter(agent=agent, scheduled_at__gte=now).select_related('client', 'listing')[:4],
            many=True,
        ).data,
        'recent_activity': ActivitySerializer(
            Activity.objects.filter(agent=agent).select_related('client')[:6], many=True
        ).data,
    })


def _greeting_note(clients, since):
    fresh = clients.filter(created_at__gte=since).count()
    if fresh == 0:
        return 'Bu hafta yangi mijoz biriktirilmadi'
    return f'Bugun {fresh} ta yangi mijoz biriktirildi'


def _pipeline_counts(deals):
    counts = {row['stage']: row['n'] for row in deals.values('stage').annotate(n=Count('id'))}
    return [{'stage': stage.value, 'count': counts.get(stage.value, 0)} for stage in DealStage]


@api_view(['GET'])
@permission_classes([IsAgent])
def rating_view(request):
    agent = request.user
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    leaderboard = (
        User.objects.filter(role=Role.AGENT, is_active=True)
        .annotate(
            month_closed=Count(
                'deals', filter=Q(deals__stage=DealStage.YOPILGAN, deals__closed_at__gte=month_start)
            ),
        )
        .order_by('-rating', '-total_deals')[:10]
    )

    board = [
        {
            'id': row.id, 'full_name': row.name, 'initials': row.initials, 'district': row.district,
            'rating': row.rating, 'tier': row.tier, 'closed_deals': row.total_deals,
            'month_deals': row.month_closed, 'is_me': row.id == agent.id,
        }
        for row in leaderboard
    ]

    my_rank = next((i + 1 for i, row in enumerate(board) if row['is_me']), None)
    percent, remaining, next_label = agent.tier_progress()

    deals = Deal.objects.filter(agent=agent)
    closed = deals.filter(stage=DealStage.YOPILGAN)
    open_deals = deals.filter(stage__in=OPEN_DEAL_STAGES).count()
    conversion = round(closed.count() / deals.count() * 100) if deals.count() else 0

    return Response({
        'agent': AgentSerializer(agent).data,
        'rank': my_rank,
        'tier': {'percent': percent, 'remaining': remaining, 'next_label': next_label, 'current': agent.tier},
        'metrics': {
            'closed_deals': closed.count(),
            'open_deals': open_deals,
            'conversion': conversion,
            'response_minutes': agent.avg_response_minutes,
            'total_commission': closed.aggregate(t=Sum('commission'))['t'] or Decimal('0'),
            'platform_paid': closed.aggregate(t=Sum('platform_cut'))['t'] or Decimal('0'),
            'avg_commission': closed.aggregate(a=Avg('commission'))['a'] or Decimal('0'),
        },
        'leaderboard': board,
    })


@api_view(['POST'])
@permission_classes([IsAgent])
def client_status_view(request, pk):
    try:
        client = Client.objects.get(pk=pk, agent=request.user)
    except Client.DoesNotExist:
        return Response({'detail': 'Mijoz topilmadi'}, status=status.HTTP_404_NOT_FOUND)

    new_status = request.data.get('status')
    valid = [choice[0] for choice in Client._meta.get_field('status').choices]
    if new_status not in valid:
        return Response({'detail': "Noto'g'ri holat"}, status=status.HTTP_400_BAD_REQUEST)

    client.status = new_status
    client.last_contact_at = timezone.now()
    client.save(update_fields=['status', 'last_contact_at'])

    Activity.objects.create(
        agent=request.user, client=client, kind='mijoz',
        text=f'{client.name} holati "{new_status}" ga o\'zgardi',
    )
    return Response(ClientSerializer(client).data)


@api_view(['POST'])
@permission_classes([AllowAny])
def lead_intake_view(request):
    """Asosiy ilova/Telegram bot/veb-sayt shu yerga xom lead yuboradi — eng mos agent
    avtomatik tanlanadi va topshiriladi (docx: "Platforma ... avtomatik mijoz beradi")."""
    serializer = LeadCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    client = assign_lead(**serializer.validated_data)
    if client is None:
        return Response({'detail': "Hozircha faol agent yo'q"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    return Response(
        {'client_id': client.id, 'agent': AgentSerializer(client.agent).data}, status=status.HTTP_201_CREATED
    )
