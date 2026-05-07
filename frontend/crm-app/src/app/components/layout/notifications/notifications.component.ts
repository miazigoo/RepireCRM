import { Component, OnInit } from '@angular/core';
import { NgIf, NgFor, NgClass, AsyncPipe } from '@angular/common';
import { Router } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatDividerModule } from '@angular/material/divider';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Observable } from 'rxjs';
import { NotificationService, Notification } from '../../../services/notification.service';

@Component({
  selector: 'app-notifications',
  standalone: true,
  imports: [
    NgIf, NgFor, NgClass, AsyncPipe,
    MatButtonModule, MatIconModule, MatDividerModule, MatTooltipModule
  ],
  templateUrl: './notifications.component.html',
  styleUrl: './notifications.component.css'
})
export class NotificationsComponent implements OnInit {
  notifications$: Observable<Notification[]>;
  unreadCount$: Observable<number>;
  connectionStatus$: Observable<boolean>;

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

  resolveColor(color: string): string {
    if (/^(#|rgb|hsl|var\()/.test(color)) {
      return color;
    }

    return `var(--color-${color}, var(--color-primary))`;
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
}
