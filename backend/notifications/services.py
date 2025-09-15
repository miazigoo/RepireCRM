
import json
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import Notification, NotificationType, NotificationSettings
from shops.models import Shop

User = get_user_model()


class NotificationService:
    """Сервис для работы с уведомлениями"""

    def __init__(self):
        self.channel_layer = get_channel_layer()

    def create_notification(
            self,
            notification_type_code: str,
            title: str,
            message: str,
            recipient=None,
            shop=None,
            role_code=None,
            priority='normal',
            related_object_type=None,
            related_object_id=None,
            data=None,
            action_url=None,
            created_by=None
    ):
        """Создать уведомление"""
        try:
            notification_type = NotificationType.objects.get(
                code=notification_type_code,
                is_active=True
            )
        except NotificationType.DoesNotExist:
            return None

        notification = Notification.objects.create(
            notification_type=notification_type,
            title=title,
            message=message,
            recipient=recipient,
            shop=shop,
            role_code=role_code,
            priority=priority,
            related_object_type=related_object_type,
            related_object_id=related_object_id,
            data=data or {},
            action_url=action_url or '',
            created_by=created_by
        )

        # Отправляем уведомление через WebSocket
        self.send_notification(notification)

        return notification

    def send_notification(self, notification: Notification):
        """Отправить уведомление через WebSocket"""
        notification_data = {
            'id': notification.id,
            'title': notification.title,
            'message': notification.message,
            'priority': notification.priority,
            'type': notification.notification_type.code,
            'icon': notification.notification_type.icon,
            'color': notification.notification_type.color,
            'action_url': notification.action_url,
            'created_at': notification.created_at.isoformat(),
            'data': notification.data
        }

        # Отправляем конкретному пользователю
        if notification.recipient:
            self._send_to_user(notification.recipient.id, notification_data)

        # Отправляем всем пользователям магазина
        elif notification.shop:
            self._send_to_shop(notification.shop.id, notification_data)

        # Отправляем пользователям с определенной ролью
        elif notification.role_code:
            self._send_to_role(notification.role_code, notification_data)

        # Помечаем как отправленное
        notification.is_sent = True
        notification.sent_at = timezone.now()
        notification.save()

    def _send_to_user(self, user_id: int, notification_data: dict):
        """Отправить уведомление пользователю"""
        if self.channel_layer:
            async_to_sync(self.channel_layer.group_send)(
                f"user_{user_id}",
                {
                    'type': 'notification_message',
                    'notification': notification_data
                }
            )

    def _send_to_shop(self, shop_id: int, notification_data: dict):
        """Отправить уведомление всем пользователям магазина"""
        if self.channel_layer:
            async_to_sync(self.channel_layer.group_send)(
                f"shop_{shop_id}",
                {
                    'type': 'notification_message',
                    'notification': notification_data
                }
            )

    def _send_to_role(self, role_code: str, notification_data: dict):
        """Отправить уведомление пользователям с определенной ролью"""
        if self.channel_layer:
            async_to_sync(self.channel_layer.group_send)(
                f"role_{role_code}",
                {
                    'type': 'notification_message',
                    'notification': notification_data
                }
            )

    def notify_order_status_change(self, order, old_status, new_status, user):
        """Уведомление об изменении статуса заказа"""
        status_labels = {
            'received': 'Принят',
            'diagnosed': 'Диагностирован',
            'in_repair': 'В ремонте',
            'ready': 'Готов к выдаче',
            'completed': 'Выдан',
            'cancelled': 'Отменен'
        }

        title = f"Изменен статус заказа {order.order_number}"
        message = f"Статус изменен с '{status_labels.get(old_status, old_status)}' на '{status_labels.get(new_status, new_status)}'"

        # Уведомляем менеджеров магазина
        self.create_notification(
            notification_type_code='order_status_change',
            title=title,
            message=message,
            shop=order.shop,
            priority='normal',
            related_object_type='order',
            related_object_id=order.id,
            action_url=f'/orders/{order.id}',
            created_by=user,
            data={
                'order_number': order.order_number,
                'customer_name': order.customer.full_name,
                'old_status': old_status,
                'new_status': new_status
            }
        )

    def notify_new_order(self, order, user):
        """Уведомление о новом заказе"""
        title = f"Новый заказ {order.order_number}"
        message = f"Создан новый заказ от клиента {order.customer.full_name}"

        self.create_notification(
            notification_type_code='new_order',
            title=title,
            message=message,
            shop=order.shop,
            priority='high',
            related_object_type='order',
            related_object_id=order.id,
            action_url=f'/orders/{order.id}',
            created_by=user,
            data={
                'order_number': order.order_number,
                'customer_name': order.customer.full_name,
                'device': f"{order.device.model.brand.name} {order.device.model.name}",
                'cost_estimate': float(order.cost_estimate)
            }
        )

    def notify_loyalty_points_earned(self, customer, points, order):
        """Уведомление о начислении баллов лояльности"""
        title = "Начислены бонусные баллы"
        message = f"За заказ {order.order_number} начислено {points} баллов"

        # Находим пользователей, которые работают с этим клиентом
        users_to_notify = User.objects.filter(
            shops=order.shop,
            role__code__in=['manager', 'cashier']
        )

        for user in users_to_notify:
            self.create_notification(
                notification_type_code='loyalty_update',
                title=title,
                message=message,
                recipient=user,
                priority='low',
                related_object_type='customer',
                related_object_id=customer.id,
                action_url=f'/customers/{customer.id}',
                data={
                    'customer_name': customer.full_name,
                    'points_earned': points,
                    'order_number': order.order_number
                }
            )

    def notify_system_alert(self, title, message, priority='normal', shop=None, role_code=None):
        """Системное уведомление"""
        self.create_notification(
            notification_type_code='system_alert',
            title=title,
            message=message,
            shop=shop,
            role_code=role_code,
            priority=priority,
            data={'system_alert': True}
        )


# Глобальный экземпляр сервиса
notification_service = NotificationService()
