# backend/notifications/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import Notification

User = get_user_model()


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Получаем пользователя из scope
        self.user = self.scope["user"]

        if isinstance(self.user, AnonymousUser):
            await self.close()
            return

        # Создаем группу для пользователя
        self.user_group_name = f"user_{self.user.id}"

        # Присоединяемся к группе пользователя
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )

        # Если у пользователя есть магазин, присоединяемся к группе магазина
        if hasattr(self.user, 'current_shop') and self.user.current_shop:
            self.shop_group_name = f"shop_{self.user.current_shop.id}"
            await self.channel_layer.group_add(
                self.shop_group_name,
                self.channel_name
            )

        # Если у пользователя есть роль, присоединяемся к группе роли
        if hasattr(self.user, 'role') and self.user.role:
            self.role_group_name = f"role_{self.user.role.code}"
            await self.channel_layer.group_add(
                self.role_group_name,
                self.channel_name
            )

        await self.accept()

        # Отправляем непрочитанные уведомления
        await self.send_unread_notifications()

    async def disconnect(self, close_code):
        # Покидаем все группы
        await self.channel_layer.group_discard(
            self.user_group_name,
            self.channel_name
        )

        if hasattr(self, 'shop_group_name'):
            await self.channel_layer.group_discard(
                self.shop_group_name,
                self.channel_name
            )

        if hasattr(self, 'role_group_name'):
            await self.channel_layer.group_discard(
                self.role_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            action = data.get('action')

            if action == 'mark_as_read':
                notification_id = data.get('notification_id')
                await self.mark_notification_as_read(notification_id)
            elif action == 'mark_all_as_read':
                await self.mark_all_notifications_as_read()
            elif action == 'get_unread_count':
                await self.send_unread_count()

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'error': 'Invalid JSON'
            }))

    async def notification_message(self, event):
        """Отправить уведомление клиенту"""
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'notification': event['notification']
        }))

    async def send_unread_notifications(self):
        """Отправить непрочитанные уведомления"""
        notifications = await self.get_unread_notifications()
        for notification in notifications:
            await self.send(text_data=json.dumps({
                'type': 'notification',
                'notification': notification
            }))

    async def send_unread_count(self):
        """Отправить количество непрочитанных уведомлений"""
        count = await self.get_unread_count()
        await self.send(text_data=json.dumps({
            'type': 'unread_count',
            'count': count
        }))

    @database_sync_to_async
    def get_unread_notifications(self):
        """Получить непрочитанные уведомления пользователя"""
        notifications = Notification.objects.filter(
            recipient=self.user,
            is_read=False
        ).select_related('notification_type')[:10]

        return [
            {
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
            for notification in notifications
        ]

    @database_sync_to_async
    def get_unread_count(self):
        """Получить количество непрочитанных уведомлений"""
        return Notification.objects.filter(
            recipient=self.user,
            is_read=False
        ).count()

    @database_sync_to_async
    def mark_notification_as_read(self, notification_id):
        """Пометить уведомление как прочитанное"""
        try:
            notification = Notification.objects.get(
                id=notification_id,
                recipient=self.user
            )
            if not notification.is_read:
                notification.is_read = True
                notification.read_at = timezone.now()
                notification.save()
            return True
        except Notification.DoesNotExist:
            return False

    @database_sync_to_async
    def mark_all_notifications_as_read(self):
        """Пометить все уведомления как прочитанные"""
        from django.utils import timezone
        Notification.objects.filter(
            recipient=self.user,
            is_read=False
        ).update(
            is_read=True,
            read_at=timezone.now()
        )
