from io import BytesIO

import qrcode
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.mail import EmailMessage
from django.utils import timezone
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from inventory.models import RetailSale

from .models import RetailDocument


def _draw_header(c, title: str, x: int, y: int):
    c.setFont("Helvetica-Bold", 12)
    c.drawString(x, y, title)
    c.setFont("Helvetica", 10)


def _draw_company_header(c, sale: RetailSale, x: int, y: int) -> int:
    sett = getattr(sale.shop, "settings", None)
    org = getattr(sett, "organization", None)
    c.setFont("Helvetica-Bold", 12)
    title = org.name if org and org.name else sale.shop.name
    c.drawString(x, y, title)
    y -= 6 * mm
    c.setFont("Helvetica", 9)
    if org:
        if org.inn or org.kpp:
            c.drawString(x, y, f"ИНН: {org.inn or '-'}  КПП: {org.kpp or '-'}")
            y -= 5 * mm
        if org.address:
            c.drawString(x, y, f"Юр. адрес: {org.address}")
            y -= 5 * mm
        # адрес точки (обязательно печатаем)
        if sale.shop.address:
            c.drawString(x, y, f"Адрес точки: {sale.shop.address}")
            y -= 5 * mm
        if org.phone or org.email:
            c.drawString(x, y, f"Тел: {org.phone or '-'}  Email: {org.email or '-'}")
            y -= 5 * mm
        if org.website:
            c.drawString(x, y, f"Сайт: {org.website}")
            y -= 5 * mm
    else:
        # нет org — печатаем сведения магазина
        if sale.shop.address:
            c.drawString(x, y, f"Адрес точки: {sale.shop.address}")
            y -= 5 * mm
        if sale.shop.phone or sale.shop.email:
            c.drawString(
                x, y, f"Тел: {sale.shop.phone or '-'}  Email: {sale.shop.email or '-'}"
            )
            y -= 5 * mm
    return y


def _draw_qr(c, x: int, y: int, data: str, size_mm: int = 30):
    qr_img = qrcode.make(data)
    buf = BytesIO()
    qr_img.save(buf, format="PNG")
    buf.seek(0)
    img = ImageReader(buf)
    c.drawImage(
        img, x, y - size_mm * mm, width=size_mm * mm, height=size_mm * mm, mask="auto"
    )
    buf.close()


def generate_invoice_pdf(sale: RetailSale) -> bytes:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    y = height - 20 * mm
    y = _draw_company_header(c, sale, 20 * mm, y)

    y -= 4 * mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(20 * mm, y, f"Квитанция {sale.sale_number}")
    y -= 8 * mm

    c.setFont("Helvetica", 10)
    c.drawString(20 * mm, y, f"Магазин: {sale.shop.name} ({sale.shop.code})")
    y -= 5 * mm
    c.drawString(
        20 * mm,
        y,
        f"Дата: {timezone.localtime(sale.completed_at or sale.created_at).strftime('%d.%m.%Y %H:%M')}",
    )
    y -= 5 * mm
    c.drawString(
        20 * mm, y, f"Кассир: {sale.cashier.get_full_name() or sale.cashier.username}"
    )
    y -= 5 * mm
    if sale.customer:
        c.drawString(20 * mm, y, f"Клиент: {sale.customer.full_name}")
        y -= 5 * mm

    y -= 6 * mm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(20 * mm, y, "Товары:")
    y -= 6 * mm
    c.setFont("Helvetica", 10)

    for line in sale.items.select_related("item").all():
        name = line.item.name
        qty = line.quantity
        price = float(line.unit_price)
        total = float(line.total_price)
        c.drawString(20 * mm, y, f"{name}  x{qty}  по {price:.2f} = {total:.2f}")
        y -= 6 * mm
        if y < 40 * mm:
            c.showPage()
            y = height - 20 * mm

    y -= 6 * mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(
        20 * mm,
        y,
        f"Итого к оплате: {float(sale.total_amount):.2f} {sale.shop.currency}",
    )
    y -= 12 * mm

    qr_data = f"SALE:{sale.sale_number}|SHOP:{sale.shop.code}|AMOUNT:{float(sale.total_amount):.2f}"
    _draw_qr(
        c,
        x=int(width - 20 * mm - 30 * mm),
        y=int(y + 30 * mm),
        data=qr_data,
        size_mm=30,
    )

    sett = getattr(sale.shop, "settings", None)
    if sett and sett.receipt_footer_text:
        c.setFont("Helvetica", 9)
        c.drawString(20 * mm, y, sett.receipt_footer_text)

    c.showPage()
    c.save()
    pdf = buf.getvalue()
    buf.close()
    return pdf


def generate_receipt_pdf(sale: RetailSale) -> bytes:
    """Термочек ~80mm ширина, простая верстка"""
    width = 58 * mm
    height = 400 * mm
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(width, height))

    y = height - 10 * mm
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(width / 2, y, sale.shop.name)
    y -= 4 * mm
    c.setFont("Helvetica", 7)
    if sale.shop.address:
        c.drawCentredString(width / 2, y, sale.shop.address[:42])
        y -= 4 * mm
    c.setFont("Helvetica", 8)
    c.drawCentredString(width / 2, y, f"{sale.shop.code}")
    y -= 8 * mm

    c.setFont("Helvetica-Bold", 9)
    c.drawString(5 * mm, y, f"Чек {sale.sale_number}")
    y -= 5 * mm
    c.setFont("Helvetica", 8)
    c.drawString(
        5 * mm,
        y,
        timezone.localtime(sale.completed_at or sale.created_at).strftime(
            "%d.%m.%Y %H:%M"
        ),
    )
    y -= 8 * mm

    c.setFont("Helvetica-Bold", 8)
    c.drawString(5 * mm, y, "Наименование")
    c.drawRightString(width - 5 * mm, y, "Сумма")
    y -= 5 * mm
    c.setFont("Helvetica", 8)

    for line in sale.items.select_related("item").all():
        name = line.item.name[:24]
        c.drawString(5 * mm, y, name)
        c.drawRightString(width - 5 * mm, y, f"{float(line.total_price):.2f}")
        y -= 4 * mm
        c.drawString(5 * mm, y, f"x{line.quantity} @ {float(line.unit_price):.2f}")
        y -= 6 * mm
        if y < 20 * mm:
            c.showPage()
            y = height - 10 * mm

    y -= 4 * mm
    c.setFont("Helvetica-Bold", 9)
    c.drawString(5 * mm, y, "ИТОГО:")
    c.drawRightString(
        width - 5 * mm, y, f"{float(sale.total_amount):.2f} {sale.shop.currency}"
    )
    y -= 8 * mm
    c.setFont("Helvetica", 8)
    c.drawCentredString(width / 2, y, "Спасибо за покупку!")
    c.showPage()
    c.save()
    pdf = buf.getvalue()
    buf.close()
    return pdf


def create_retail_pdf_and_store(sale: RetailSale, doc_type: str) -> RetailDocument:
    """Сгенерировать PDF и сохранить RetailDocument"""
    if doc_type == RetailDocument.DocumentType.RETAIL_RECEIPT:
        pdf = generate_receipt_pdf(sale)
    else:
        pdf = generate_invoice_pdf(sale)

    filename = f"{doc_type}-{sale.sale_number}.pdf"
    doc = RetailDocument.objects.create(
        sale=sale,
        document_type=doc_type,
    )
    doc.file.save(filename, ContentFile(pdf), save=True)
    return doc


def send_retail_receipt_email(
    to_email: str, sale: RetailSale, doc: RetailDocument
) -> bool:
    """Отправка PDF на email"""
    subject = f"Чек {sale.sale_number}"
    body = f"Добрый день!\nВаш чек по продаже {sale.sale_number} во вложении."
    email = EmailMessage(subject, body, settings.DEFAULT_FROM_EMAIL, [to_email])
    # прикрепляем файл
    doc.file.open("rb")
    email.attach(doc.file.name.split("/")[-1], doc.file.read(), "application/pdf")
    doc.file.close()
    try:
        email.send(fail_silently=False)
        return True
    except Exception:
        return False
