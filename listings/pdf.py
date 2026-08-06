"""docx 2.2-band: "Onlayn shartnoma: Platforma avtomatik ravishda shartnoma
yaratadi (PDF/E-imzo)". Bu yerda haqiqiy PDF fayl generatsiya qilinadi.
"""
import io

from django.core.files.base import ContentFile
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


def render_contract_pdf(contract):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    y = height - 25 * mm

    def line(text, size=11, gap=8 * mm, bold=False):
        nonlocal y
        c.setFont('Helvetica-Bold' if bold else 'Helvetica', size)
        c.drawString(20 * mm, y, text)
        y -= gap

    line(f'Uyimiz.uz — Oldi-sotdi/ijara shartnomasi №C-{contract.id}', 14, bold=True)
    line(f"Tuzilgan sana: {contract.created_at:%Y-%m-%d %H:%M}")
    line('')
    line(f"E'lon: #{contract.listing_id} — {contract.listing.district}, {contract.listing.address}")
    line(f'Bitim turi: {contract.get_deal_display()}')
    line(f'Narx: {contract.price} {contract.currency.upper()}')
    if contract.service_fee:
        line(f"Platforma xizmat haqi: {contract.service_fee:,.0f} so'm".replace(',', ' '))
    line('')
    line(f'Sotuvchi: {contract.seller.name} ({contract.seller.phone})', bold=True)
    line(f'Xaridor/Ijarachi: {contract.buyer.name} ({contract.buyer.phone})', bold=True)
    if contract.agent_id:
        line(f'Uyimiz Agent: {contract.agent.name} ({contract.agent.phone})')
    line('')
    line(f"Sotuvchi imzoladi: {'Ha' if contract.seller_signed else 'Yoq'}")
    line(f"Xaridor imzoladi: {'Ha' if contract.buyer_signed else 'Yoq'}")
    line('')
    line('Ushbu hujjat Uyimiz.uz platformasi tomonidan avtomatik yaratilgan', 9)
    line('va elektron imzo (E-IMZO) integratsiyasi qo\'shilgunga qadar demo hisoblanadi.', 9)

    c.showPage()
    c.save()
    buf.seek(0)
    filename = f'shartnoma-C-{contract.id}.pdf'
    contract.pdf.save(filename, ContentFile(buf.read()), save=False)
    return contract
