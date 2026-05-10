import { Component, OnInit } from '@angular/core';
import { NgIf, NgFor, NgClass, AsyncPipe } from '@angular/common';
import { Router } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Observable } from 'rxjs';
import { NotificationService, Notification } from '../../../services/notification.service';

type NotificationGlyph = 'task' | 'order' | 'inventory' | 'system' | 'report' | 'comment' | 'warning' | 'event';

@Component({
  selector: 'app-notifications',
  standalone: true,
  imports: [
    NgIf, NgFor, NgClass, AsyncPipe,
    MatButtonModule, MatTooltipModule
  ],
  templateUrl: './notifications.component.html',
  styleUrl: './notifications.component.scss'
})
export class NotificationsComponent implements OnInit {
  notifications$: Observable<Notification[]>;
  unreadCount$: Observable<number>;
  connectionStatus$: Observable<boolean>;

  private readonly notificationIconPaths: Record<NotificationGlyph, string[]> = {
    task: [
      'M8.5 5.5h7',
      'M9 4h6',
      'M6.5 5.5h11A1.5 1.5 0 0 1 19 7v12a1.5 1.5 0 0 1-1.5 1.5h-11A1.5 1.5 0 0 1 5 19V7a1.5 1.5 0 0 1 1.5-1.5Z',
      'm8.5 13 2 2 5-5'
    ],
    order: [
      'M6 3.5h12v17l-3-1.8-3 1.8-3-1.8-3 1.8Z',
      'M9 8h6',
      'M9 12h6',
      'M9 16h3.8'
    ],
    inventory: [
      'M4.5 8.5 12 4l7.5 4.5-7.5 4.5Z',
      'M4.5 8.5v7L12 20l7.5-4.5v-7',
      'M12 13v7'
    ],
    system: [
      'M12 8.5a3.5 3.5 0 1 1 0 7 3.5 3.5 0 0 1 0-7Z',
      'M12 3.8v2.1',
      'M12 18.1v2.1',
      'M5.4 5.4 6.9 6.9',
      'm17.1 17.1 1.5 1.5',
      'M3.8 12h2.1',
      'M18.1 12h2.1',
      'm5.4 18.6 1.5-1.5',
      'm17.1 6.9 1.5-1.5'
    ],
    report: [
      'M5.5 4.5h9L18.5 8v11.5h-13Z',
      'M14.5 4.5V8h4',
      'M8.5 16v-4',
      'M12 16V9.5',
      'M15.5 16v-2.5'
    ],
    comment: [
      'M5 6.5A2.5 2.5 0 0 1 7.5 4h9A2.5 2.5 0 0 1 19 6.5v6A2.5 2.5 0 0 1 16.5 15H11l-4.5 4v-4A2.5 2.5 0 0 1 4 12.5Z',
      'M8 8h8',
      'M8 11.5h5.5'
    ],
    warning: [
      'M12 4 21 20H3Z',
      'M12 9v4',
      'M12 17h.01'
    ],
    event: [
      'M5 6.5A2.5 2.5 0 0 1 7.5 4h9A2.5 2.5 0 0 1 19 6.5v7A2.5 2.5 0 0 1 16.5 16H12l-4.5 4v-4A2.5 2.5 0 0 1 5 13.5Z',
      'M8.5 8h7',
      'M8.5 11.5h4'
    ],
  };

  private readonly notificationIconAliases: Record<string, NotificationGlyph> = {
    task: 'task',
    task_assigned: 'task',
    assignment: 'task',
    assignment_ind: 'task',
    add_task: 'task',
    task_status_change: 'task',
    published_with_changes: 'task',
    task_comment: 'comment',
    comment: 'comment',
    task_overdue: 'warning',
    warning: 'warning',
    low_stock: 'inventory',
    inventory: 'inventory',
    inventory_2: 'inventory',
    order: 'order',
    order_status: 'order',
    order_status_change: 'order',
    new_order: 'order',
    receipt: 'order',
    system: 'system',
    system_alert: 'system',
    settings: 'system',
    report: 'report',
    reports: 'report',
    loyalty_update: 'report',
  };

  constructor(
    private notificationService: NotificationService,
    private router: Router
  ) {
    this.notifications$ = this.notificationService.notifications$;
    this.unreadCount$ = this.notificationService.unreadCount$;
    this.connectionStatus$ = this.notificationService.connectionStatus$;
  }

  ngOnInit(): void {
    this.notificationService.refresh();
    this.notificationService.requestNotificationPermission();
  }

  onNotificationClick(notification: Notification): void {
    this.notificationService.markAsRead(notification.id);

    if (notification.action_url) {
      this.router.navigateByUrl(notification.action_url);
    }
  }

  refresh(): void {
    this.notificationService.refresh();
  }

  markAllAsRead(): void {
    this.notificationService.markAllAsRead();
  }

  trackByNotificationId(_: number, notification: Notification): number {
    return notification.id;
  }

  getUnreadTotal(notifications: Notification[]): number {
    return notifications.filter(notification => notification.is_read !== true).length;
  }

  getPriorityTotal(notifications: Notification[], priorities: Notification['priority'][]): number {
    return notifications.filter(notification => priorities.includes(notification.priority)).length;
  }

  getTypeLabel(type: string): string {
    const labels: Record<string, string> = {
      low_stock: 'Склад',
      order_status: 'Заказ',
      order_status_change: 'Заказ',
      new_order: 'Новый заказ',
      system: 'Система',
      system_alert: 'Система',
      task: 'Задача',
      task_assigned: 'Задача',
      task_status_change: 'Задача',
      task_comment: 'Комментарий',
      task_overdue: 'Просрочка',
      report: 'Отчет',
      loyalty_update: 'Лояльность'
    };

    return labels[type] || 'Событие';
  }

  getPriorityClass(priority: string): string {
    switch (priority) {
      case 'urgent': return 'priority-urgent';
      case 'high': return 'priority-high';
      case 'normal': return 'priority-normal';
      case 'low': return 'priority-low';
      default: return 'priority-normal';
    }
  }

  getPriorityIcon(priority: string): string {
    switch (priority) {
      case 'urgent': return 'priority_high';
      case 'high': return 'keyboard_arrow_up';
      case 'normal': return 'remove';
      case 'low': return 'keyboard_arrow_down';
      default: return 'remove';
    }
  }

  getPriorityLabel(priority: string): string {
    switch (priority) {
      case 'urgent': return 'Срочно';
      case 'high': return 'Высокий приоритет';
      case 'normal': return 'Обычный приоритет';
      case 'low': return 'Низкий приоритет';
      default: return 'Обычный приоритет';
    }
  }

  getNotificationIconPaths(notification: Notification): string[] {
    return this.notificationIconPaths[this.getNotificationGlyph(notification)];
  }

  getPriorityIconPaths(priority: string): string[] {
    switch (priority) {
      case 'urgent':
        return ['M12 4 21 20H3Z', 'M12 9v4', 'M12 17h.01'];
      case 'high':
        return ['M12 5v14', 'm7.2 10.8-5.2-5.2-5.2 5.2'];
      case 'low':
        return ['M12 19V5', 'm6.8 13.2 5.2 5.2 5.2-5.2'];
      default:
        return ['M6 12h12'];
    }
  }

  resolveNotificationColor(notification: Notification): string {
    const fallbackByGlyph: Record<NotificationGlyph, string> = {
      task: 'var(--color-primary)',
      order: 'var(--color-success)',
      inventory: 'var(--color-warning)',
      system: 'var(--color-accent)',
      report: 'var(--color-accent)',
      comment: 'var(--color-primary)',
      warning: 'var(--color-danger)',
      event: 'var(--color-primary)',
    };

    return this.resolveColor(notification.color, fallbackByGlyph[this.getNotificationGlyph(notification)]);
  }

  resolveColor(color?: string | null, fallback = 'var(--color-primary)'): string {
    const normalized = (color || '').trim();

    if (!normalized) {
      return fallback;
    }

    if (/^(#|rgb|hsl|var\()/.test(normalized)) {
      return normalized;
    }

    const aliases: Record<string, string> = {
      warn: 'danger',
      warning: 'warning',
      danger: 'danger',
      accent: 'accent',
      primary: 'primary',
      success: 'success',
    };
    const token = aliases[normalized] || normalized;

    return `var(--color-${token}, ${fallback})`;
  }

  trackBySvgPath(_: number, path: string): string {
    return path;
  }

  getRelativeTime(dateString: string): string {
    const date = new Date(dateString);
    const now = new Date();
    const diffInMinutes = Math.floor((now.getTime() - date.getTime()) / (1000 * 60));

    if (diffInMinutes < 1) return 'Только что';
    if (diffInMinutes < 60) return `${diffInMinutes} мин. назад`;

    const diffInHours = Math.floor(diffInMinutes / 60);
    if (diffInHours < 24) return `${diffInHours} ч. назад`;

    const diffInDays = Math.floor(diffInHours / 24);
    if (diffInDays < 7) return `${diffInDays} дн. назад`;

    return date.toLocaleDateString();
  }

  private getNotificationGlyph(notification: Notification): NotificationGlyph {
    const type = (notification.type || '').toLowerCase();
    const icon = (notification.icon || '').toLowerCase();

    return this.notificationIconAliases[type] || this.notificationIconAliases[icon] || 'event';
  }
}
