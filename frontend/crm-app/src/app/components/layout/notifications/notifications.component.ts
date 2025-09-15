// frontend/crm-app/src/app/components/layout/notifications/notifications.component.ts
import { Component, OnInit, OnDestroy } from '@angular/core';
import { NgIf, NgFor, DatePipe } from '@angular/common';
import { Router } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatBadgeModule } from '@angular/material/badge';
import { MatMenuModule } from '@angular/material/menu';
import { MatListModule } from '@angular/material/list';
import { MatDividerModule } from '@angular/material/divider';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Observable, Subscription } from 'rxjs';
import { NotificationService, Notification } from '../../../services/notification.service';

@Component({
  selector: 'app-notifications',
  standalone: true,
  imports: [
    NgIf, NgFor, DatePipe,
    MatButtonModule, MatIconModule, MatBadgeModule,
    MatMenuModule, MatListModule, MatDividerModule, MatTooltipModule
  ],
  templateUrl: './notifications.component.html',
  styleUrl: './notifications.component.css'
})
export class NotificationsComponent implements OnInit, OnDestroy {
  notifications$: Observable<Notification[]>;
  unreadCount$: Observable<number>;
  connectionStatus$: Observable<boolean>;

  private subscription = new Subscription();

  constructor(
    private notificationService: NotificationService,
    private router: Router
  ) {
    this.notifications$ = this.notificationService.notifications$;
    this.unreadCount$ = this.notificationService.unreadCount$;
    this.connectionStatus$ = this.notificationService.connectionStatus$;
  }

  ngOnInit(): void {
    // Request notification permission on component init
    this.notificationService.requestNotificationPermission();
  }

  ngOnDestroy(): void {
    this.subscription.unsubscribe();
  }

  onNotificationClick(notification: Notification): void {
    // Mark as read
    this.notificationService.markAsRead(notification.id);

    // Navigate if action URL is provided
    if (notification.action_url) {
      this.router.navigate([notification.action_url]);
    }
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
