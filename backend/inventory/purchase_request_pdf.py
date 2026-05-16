from io import BytesIO
from pathlib import Path
from textwrap import shorten

from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from .models import PurchaseRequest, PurchaseRequestBatch

FONT_REGULAR = "Helvetica"
FONT_BOLD = "Helvetica-Bold"


def _register_fonts() -> None:
    global FONT_REGULAR, FONT_BOLD
    candidates = [
        (
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ),
        (
            "/usr/share/fonts/truetype/msttcorefonts/Arial.ttf",
            "/usr/share/fonts/truetype/msttcorefonts/Arial_Bold.ttf",
        ),
    ]
    for regular_path, bold_path in candidates:
        if Path(regular_path).exists() and Path(bold_path).exists():
            if "RepairCRM-Regular" not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont("RepairCRM-Regular", regular_path))
            if "RepairCRM-Bold" not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont("RepairCRM-Bold", bold_path))
            FONT_REGULAR = "RepairCRM-Regular"
            FONT_BOLD = "RepairCRM-Bold"
            return


def _money(value) -> str:
    return f"{float(value or 0):,.2f}".replace(",", " ") + " ₽"


def _date_time(value) -> str:
    return timezone.localtime(value).strftime("%d.%m.%Y %H:%M")


def _safe(value: object, fallback: str = "-") -> str:
    text = str(value or "").strip()
    return text or fallback


def _draw_wrapped(
    pdf: canvas.Canvas,
    text: str,
    x: float,
    y: float,
    width: float,
    font: str | None = None,
    size: int = 8,
    leading: float = 4.2 * mm,
    max_lines: int = 2,
) -> float:
    font = font or FONT_REGULAR
    pdf.setFont(font, size)
    words = _safe(text, "").split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if pdf.stringWidth(candidate, font, size) <= width:
            current = candidate
            continue
        if current:
            lines.append(current)
        current = word
        if len(lines) >= max_lines:
            break
    if current and len(lines) < max_lines:
        lines.append(current)
    if not lines:
        lines = ["-"]
    if len(lines) == max_lines and words:
        lines[-1] = shorten(lines[-1], width=48, placeholder="...")

    current_y = y
    for line in lines[:max_lines]:
        pdf.drawString(x, current_y, line)
        current_y -= leading
    return current_y


def _organization_for(purchase_request: PurchaseRequest):
    try:
        settings = getattr(purchase_request.shop, "settings", None)
    except ObjectDoesNotExist:
        settings = None
    return getattr(settings, "organization", None)


def _append_contact(lines: list[str], prefix: str, phone: str = "", email: str = ""):
    parts = [part for part in (phone, email) if part]
    if parts:
        lines.append(f"{prefix}: {' · '.join(parts)}")


def _fit_line(pdf: canvas.Canvas, text: str, width: float, font: str, size: int) -> str:
    value = _safe(text)
    if pdf.stringWidth(value, font, size) <= width:
        return value
    while len(value) > 4 and pdf.stringWidth(f"{value}...", font, size) > width:
        value = value[:-1]
    return f"{value}..."


def _draw_info_box(
    pdf: canvas.Canvas,
    x: float,
    y: float,
    width: float,
    height: float,
    title: str,
    lines: list[str],
    accent: str = "#111827",
) -> None:
    pdf.setFillColor(colors.HexColor("#F8FAFC"))
    pdf.roundRect(x, y - height, width, height, 2 * mm, stroke=0, fill=1)
    pdf.setStrokeColor(colors.HexColor("#E5E7EB"))
    pdf.roundRect(x, y - height, width, height, 2 * mm, stroke=1, fill=0)

    pdf.setFillColor(colors.HexColor(accent))
    pdf.setFont(FONT_BOLD, 8)
    pdf.drawString(x + 4 * mm, y - 6 * mm, title)

    current_y = y - 12 * mm
    pdf.setFillColor(colors.HexColor("#374151"))
    pdf.setFont(FONT_REGULAR, 7)
    for line in lines[:5]:
        pdf.drawString(
            x + 4 * mm,
            current_y,
            _fit_line(pdf, line, width - 8 * mm, FONT_REGULAR, 7),
        )
        current_y -= 4.2 * mm


def _draw_header(pdf: canvas.Canvas, purchase_request: PurchaseRequest, title: str):
    width, height = A4
    organization = _organization_for(purchase_request)
    company_name = (
        organization.name
        if organization and organization.name
        else purchase_request.shop.name
    )

    pdf.setFillColor(colors.HexColor("#111827"))
    pdf.rect(0, height - 34 * mm, width, 34 * mm, stroke=0, fill=1)
    pdf.setFillColor(colors.white)
    pdf.setFont(FONT_BOLD, 18)
    pdf.drawString(18 * mm, height - 16 * mm, title)
    pdf.setFont(FONT_REGULAR, 9)
    request_meta = (
        f"{purchase_request.request_number} · "
        f"{_date_time(purchase_request.created_at)}"
    )
    pdf.drawString(
        18 * mm,
        height - 24 * mm,
        request_meta,
    )

    pdf.setFont(FONT_BOLD, 10)
    pdf.drawRightString(width - 18 * mm, height - 16 * mm, company_name[:44])
    pdf.setFont(FONT_REGULAR, 8)
    pdf.drawRightString(
        width - 18 * mm,
        height - 23 * mm,
        f"{purchase_request.shop.name} · {purchase_request.shop.code}",
    )
    if organization and (organization.inn or organization.kpp):
        pdf.drawRightString(
            width - 18 * mm,
            height - 29 * mm,
            f"ИНН {organization.inn or '-'} · КПП {organization.kpp or '-'}",
        )


def _draw_meta(
    pdf: canvas.Canvas,
    purchase_request: PurchaseRequest,
    batch: PurchaseRequestBatch | None,
    y: float,
) -> float:
    left_x = 18 * mm
    right_x = 107 * mm
    box_width = 85 * mm
    box_height = 35 * mm
    row_gap = 6 * mm

    creator = (
        purchase_request.created_by.get_full_name()
        or purchase_request.created_by.username
    )
    due_date = (
        purchase_request.due_date.strftime("%d.%m.%Y")
        if purchase_request.due_date
        else "Не указан"
    )
    supplier = batch.supplier if batch and batch.supplier else None
    supplier_name = supplier.name if supplier else "Не выбран"
    group_name = (
        batch.procurement_group.name
        if batch and batch.procurement_group
        else "Смешанная заявка"
    )
    organization = _organization_for(purchase_request)

    sender_lines = [
        organization.name if organization else purchase_request.shop.name,
    ]
    if organization and (organization.inn or organization.kpp):
        sender_lines.append(
            f"ИНН: {organization.inn or '-'} · КПП: {organization.kpp or '-'}"
        )
    if organization and organization.address:
        sender_lines.append(f"Юр. адрес: {organization.address}")
    if purchase_request.shop.address:
        sender_lines.append(f"Точка: {purchase_request.shop.address}")
    _append_contact(
        sender_lines,
        "Контакты",
        organization.phone if organization else purchase_request.shop.phone,
        organization.email if organization else purchase_request.shop.email,
    )

    supplier_lines = [supplier_name]
    if supplier:
        if supplier.contact_person:
            supplier_lines.append(f"Контакт: {supplier.contact_person}")
        _append_contact(supplier_lines, "Связь", supplier.phone, supplier.email)
        if supplier.address:
            supplier_lines.append(f"Адрес: {supplier.address}")
        if supplier.payment_terms or supplier.delivery_terms:
            payment_terms = supplier.payment_terms or "-"
            delivery_terms = supplier.delivery_terms or "-"
            supplier_lines.append(f"Условия: {payment_terms} / {delivery_terms}")

    document_lines = [
        f"Создал: {creator}",
        f"Приоритет: {purchase_request.get_priority_display()}",
        f"Желаемый срок: {due_date}",
        f"Статус: {purchase_request.get_status_display()}",
        f"Группа: {group_name}",
    ]

    comment = (batch.notes if batch and batch.notes else purchase_request.notes).strip()
    comment_lines = [
        comment or "Комментарий не указан",
        f"Сформировано: {_date_time(timezone.now())}",
    ]
    if batch:
        comment_lines.append(f"Документ: {batch.batch_number}")

    _draw_info_box(pdf, left_x, y, box_width, box_height, "Отправитель", sender_lines)
    _draw_info_box(pdf, right_x, y, box_width, box_height, "Получатель", supplier_lines)
    second_y = y - box_height - row_gap
    _draw_info_box(
        pdf, left_x, second_y, box_width, 30 * mm, "Параметры", document_lines
    )
    _draw_info_box(
        pdf,
        right_x,
        second_y,
        box_width,
        30 * mm,
        "Комментарий",
        comment_lines,
        accent="#2563EB",
    )
    return second_y - 36 * mm


def _draw_table_header(pdf: canvas.Canvas, y: float) -> float:
    pdf.setFillColor(colors.HexColor("#E5E7EB"))
    pdf.rect(18 * mm, y - 7 * mm, 174 * mm, 7 * mm, stroke=0, fill=1)
    pdf.setFillColor(colors.HexColor("#111827"))
    pdf.setFont(FONT_BOLD, 7)
    headers = [
        (20, "Артикул"),
        (43, "Наименование"),
        (101, "Группа"),
        (126, "Кол-во"),
        (142, "Цена"),
        (164, "Сумма"),
    ]
    for x_mm, label in headers:
        pdf.drawString(x_mm * mm, y - 4.8 * mm, label)
    return y - 9 * mm


def _new_page(
    pdf: canvas.Canvas, purchase_request: PurchaseRequest, title: str
) -> float:
    pdf.showPage()
    _draw_header(pdf, purchase_request, title)
    return _draw_table_header(pdf, A4[1] - 42 * mm)


def generate_purchase_request_pdf(
    purchase_request: PurchaseRequest, batch: PurchaseRequestBatch | None = None
) -> bytes:
    _register_fonts()
    buf = BytesIO()
    pdf = canvas.Canvas(buf, pagesize=A4)
    title = "Заявка поставщику"
    if batch:
        title = f"Документ поставщику {batch.batch_number}"

    _draw_header(pdf, purchase_request, title)
    y = _draw_meta(pdf, purchase_request, batch, A4[1] - 42 * mm)

    y = _draw_table_header(pdf, y)

    if batch:
        lines = batch.items.select_related(
            "request_item__item",
            "request_item__procurement_group",
        ).order_by("id")
        total_amount = batch.total_amount
    else:
        lines = purchase_request.items.select_related(
            "item", "procurement_group"
        ).order_by("id")
        total_amount = purchase_request.total_amount

    row_index = 1
    for line in lines:
        if y < 35 * mm:
            y = _new_page(pdf, purchase_request, title)

        request_item = line.request_item if batch else line
        item = request_item.item
        quantity = line.quantity if batch else request_item.approved_quantity
        unit_price = line.unit_price if batch else request_item.unit_price
        total_price = line.total_price if batch else request_item.total_price
        group = request_item.procurement_group
        group_name = group.name if group else "Без группы"

        pdf.setFillColor(colors.HexColor("#111827"))
        pdf.setFont(FONT_REGULAR, 7)
        pdf.drawRightString(17 * mm, y, str(row_index))
        pdf.drawString(20 * mm, y, _safe(item.sku))
        _draw_wrapped(pdf, item.name, 43 * mm, y, 54 * mm, size=7, max_lines=2)
        _draw_wrapped(pdf, group_name, 101 * mm, y, 22 * mm, size=7, max_lines=2)
        pdf.drawRightString(137 * mm, y, str(quantity))
        pdf.drawRightString(160 * mm, y, _money(unit_price))
        pdf.drawRightString(190 * mm, y, _money(total_price))
        y -= 12 * mm
        row_index += 1

    pdf.setStrokeColor(colors.HexColor("#D1D5DB"))
    pdf.line(18 * mm, y + 3 * mm, 192 * mm, y + 3 * mm)
    y -= 5 * mm
    pdf.setFont(FONT_BOLD, 11)
    pdf.setFillColor(colors.HexColor("#111827"))
    pdf.drawRightString(158 * mm, y, "Итого:")
    pdf.drawRightString(192 * mm, y, _money(total_amount))

    y -= 18 * mm
    pdf.setFont(FONT_REGULAR, 8)
    pdf.drawString(18 * mm, y, "Ответственный: __________________________")
    pdf.drawRightString(192 * mm, y, "Подпись: __________________")

    pdf.showPage()
    pdf.save()
    body = buf.getvalue()
    buf.close()
    return body
