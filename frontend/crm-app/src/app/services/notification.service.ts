import { Injectable } from '@angular/core';
import { BehaviorSubject, of } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { environment } from '../../environments/environment';
import { ApiService } from './api.service';

export interface Notification {
  id: number;
  title: string;
  message: string;
  priority: 'low' | 'normal' | 'high' | 'urgent';
  type: string;
  icon: string;
  color: string;
  action_url?: string;
  created_at: string;
  data?: any;
  is_read?: boolean;
  read_at?: string | null;
}

@Injectable({
  providedIn: 'root'
})
export class NotificationService {
  private socket: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectInterval = 5000;

  private notificationsSubject = new BehaviorSubject<Notification[]>([]);
  private unreadCountSubject = new BehaviorSubject<number>(0);
  private connectionStatusSubject = new BehaviorSubject<boolean>(false);

  public notifications$ = this.notificationsSubject.asObservable();
  public unreadCount$ = this.unreadCountSubject.asObservable();
  public connectionStatus$ = this.connectionStatusSubject.asObservable();

  constructor(private apiService: ApiService) {
    this.refresh();
    this.connect();
  }

  public refresh(): void {
    if (!localStorage.getItem('access_token')) {
      return;
    }

    this.apiService.get<Notification[]>('/notifications/', { limit: 20, unread_only: false }).pipe(
      catchError(() => {
        this.connectionStatusSubject.next(false);
        return of([]);
      })
    ).subscribe((notifications) => {
      this.syncNotifications(notifications);
      this.connectionStatusSubject.next(true);
    });
  }

  private connect(): void {
    if (!environment.production) {
      return;
    }

    const token = localStorage.getItem('access_token');
    if (!token) {
      return;
    }

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/ws/notifications/`;

    this.socket = new WebSocket(wsUrl);

    this.socket.onopen = () => {
      console.log('WebSocket connected');
      this.connectionStatusSubject.next(true);
      this.reconnectAttempts = 0;

      // Запрашиваем количество непрочитанных уведомлений
      this.sendMessage({ action: 'get_unread_count' });
    };

    this.socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.handleMessage(data);
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };

    this.socket.onclose = () => {
      console.log('WebSocket disconnected');
      this.connectionStatusSubject.next(false);
      this.attemptReconnect();
    };

    this.socket.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }

  private handleMessage(data: any): void {
    switch (data.type) {
      case 'notification':
        this.addNotification(data.notification);
        break;
      case 'unread_count':
        this.unreadCountSubject.next(data.count);
        break;
      case 'error':
        console.error('WebSocket error:', data.error);
        break;
    }
  }

  private addNotification(notification: Notification): void {
    const currentNotifications = this.notificationsSubject.value;
    const updatedNotifications = [
      { ...notification, is_read: notification.is_read ?? false },
      ...currentNotifications.filter((item) => item.id !== notification.id)
    ].slice(0, 50); // Keep last 50
    this.syncNotifications(updatedNotifications);

    if (notification.is_read !== true) {
      this.showBrowserNotification(notification);
    }
  }

  private showBrowserNotification(notification: Notification): void {
    if ('Notification' in window && Notification.permission === 'granted') {
      const browserNotification = new Notification(notification.title, {
        body: notification.message,
        icon: '/favicon.ico',
        tag: notification.id.toString()
      });

      browserNotification.onclick = () => {
        window.focus();
        if (notification.action_url) {
          // Navigate to the URL (you might need to inject Router here)
          window.location.href = notification.action_url;
        }
        browserNotification.close();
      };

      // Auto close after 5 seconds
      setTimeout(() => {
        browserNotification.close();
      }, 5000);
    }
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      console.log(`Attempting to reconnect... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);

      setTimeout(() => {
        this.connect();
      }, this.reconnectInterval);
    } else {
      console.error('Max reconnection attempts reached');
    }
  }

  private sendMessage(message: any): void {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(message));
    }
  }

  private syncNotifications(notifications: Notification[]): void {
    const normalized = notifications.map((notification) => ({
      ...notification,
      is_read: notification.is_read ?? false
    }));
    this.notificationsSubject.next(normalized);
    this.unreadCountSubject.next(normalized.filter((notification) => !notification.is_read).length);
  }

  public markAsRead(notificationId: number): void {
    this.sendMessage({
      action: 'mark_as_read',
      notification_id: notificationId
    });

    const currentNotifications = this.notificationsSubject.value;
    const updatedNotifications = currentNotifications.map(
      notification => notification.id === notificationId
        ? { ...notification, is_read: true, read_at: notification.read_at || new Date().toISOString() }
        : notification
    );
    this.syncNotifications(updatedNotifications);

    this.apiService.post(`/notifications/${notificationId}/mark-read`, {}).subscribe({
      error: () => this.refresh()
    });
  }

  public markAllAsRead(): void {
    this.sendMessage({ action: 'mark_all_as_read' });

    const updatedNotifications = this.notificationsSubject.value.map(notification => ({
      ...notification,
      is_read: true,
      read_at: notification.read_at || new Date().toISOString()
    }));
    this.syncNotifications(updatedNotifications);

    this.apiService.post('/notifications/mark-all-read', {}).subscribe({
      error: () => this.refresh()
    });
  }

  public requestNotificationPermission(): void {
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission().then(permission => {
        console.log('Notification permission:', permission);
      });
    }
  }

  public disconnect(): void {
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
  }
}
