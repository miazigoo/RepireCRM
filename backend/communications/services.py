import logging
from typing import Optional

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


class CommunicationService:
    def send_ready_email(self, to_email: str, order_number: str, shop_name: str):
        if not settings.COMMUNICATIONS_ENABLE_EMAIL:
            return False
        subject = f"Заказ {order_number} готов к выдаче"
        message = f"Ваш заказ {order_number} готов к выдаче в магазине {shop_name}. Спасибо, что выбрали нас!"
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [to_email],
                fail_silently=False,
            )
            return True
        except Exception as e:
            logger.exception("Email send failed: %s", e)
            return False

    def send_ready_sms(self, to_phone: str, order_number: str, shop_name: str):
        if not settings.COMMUNICATIONS_ENABLE_SMS:
            return False
        if not (
            settings.TWILIO_ACCOUNT_SID
            and settings.TWILIO_AUTH_TOKEN
            and settings.TWILIO_FROM_NUMBER
        ):
            logger.warning("Twilio not configured, SMS skipped")
            return False
        try:
            from twilio.rest import Client

            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            body = f"Ваш заказ {order_number} готов к выдаче. {shop_name}"
            client.messages.create(
                body=body,
                from_=settings.TWILIO_FROM_NUMBER,
                to=str(to_phone),
            )
            return True
        except Exception as e:
            logger.exception("SMS send failed: %s", e)
            return False

    def notify_ready(self, customer, order):
        """
        Уведомления клиенту о статусе READY.
        - Учитывает согласие marketing_consent (если False — не отправляем).
        - Учитывает preferred_channel: 'email' | 'sms' | None (оба).
        """
        ok_email = False
        ok_sms = False

        # Учитываем согласие
        if hasattr(customer, "marketing_consent") and not customer.marketing_consent:
            logger.info(
                "Skip communications for customer %s due to marketing_consent=False",
                customer.id,
            )
            return {"email_sent": False, "sms_sent": False, "skipped": "no_consent"}

        channel = getattr(customer, "preferred_channel", None)

        if channel == "email":
            if customer.email:
                ok_email = self.send_ready_email(
                    customer.email, order.order_number, order.shop.name
                )
        elif channel == "sms":
            if customer.phone:
                ok_sms = self.send_ready_sms(
                    customer.phone, order.order_number, order.shop.name
                )
        else:
            # не указано — пытаемся оба
            if customer.email:
                ok_email = self.send_ready_email(
                    customer.email, order.order_number, order.shop.name
                )
            if customer.phone:
                ok_sms = self.send_ready_sms(
                    customer.phone, order.order_number, order.shop.name
                )

        return {"email_sent": ok_email, "sms_sent": ok_sms}


communication_service = CommunicationService()
