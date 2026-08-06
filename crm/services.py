"""docx 5-band: "Platforma bitimlar orqali ularga avtomatik mijoz (lead) beradi"
va "Har bir makler ... hudud ... bo'yicha" — shu yerda amalga oshiriladi.
"""
from accounts.models import CertificationStatus, Role, User


def pick_best_agent(district=''):
    """Berilgan hududdagi eng yuqori reytingli tasdiqlangan agentni tanlaydi.

    Hududda agent topilmasa — umuman eng yaxshi tasdiqlangan agent qaytadi.
    """
    qs = User.objects.filter(role=Role.AGENT, is_active=True, certification=CertificationStatus.TASDIQLANGAN)
    if district:
        by_district = qs.filter(district=district).order_by('-rating', '-total_deals')
        agent = by_district.first()
        if agent:
            return agent
    return qs.order_by('-rating', '-total_deals').first()


def assign_lead(*, name, phone, request_text, district='', deal_type=None, budget_label='', source=None, note=''):
    """Yangi mijozni eng mos agentga avtomatik biriktiradi va Activity yozadi."""
    from .models import Activity, ActivityKind, Client, DealType, LeadSource

    agent = pick_best_agent(district)
    if agent is None:
        return None

    client = Client.objects.create(
        agent=agent,
        name=name,
        phone=phone,
        request=request_text,
        deal_type=deal_type or DealType.SOTIB_OLISH,
        district=district,
        budget_label=budget_label,
        source=source or LeadSource.WEB,
        note=note,
    )
    Activity.objects.create(
        agent=agent,
        client=client,
        kind=ActivityKind.MIJOZ,
        text=f'Yangi mijoz avtomatik biriktirildi: {client.name}',
    )
    return client
