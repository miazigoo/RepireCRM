import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { provideRouter } from '@angular/router';
import { of } from 'rxjs';
import { NotificationService, Notification } from '../../../services/notification.service';
import { NotificationsComponent } from './notifications.component';

describe('NotificationsComponent', () => {
  let fixture: ComponentFixture<NotificationsComponent>;
  let notificationService: jasmine.SpyObj<NotificationService>;

  const notifications: Notification[] = [
    {
      id: 10,
      title: 'Заканчиваются чехлы',
      message: 'Осталось 2 позиции на складе',
      priority: 'high',
      type: 'low_stock',
      icon: 'inventory_2',
      color: '#f59e0b',
      action_url: '/inventory',
      created_at: '2026-05-07T10:00:00Z',
      is_read: false,
    },
  ];

  beforeEach(async () => {
    notificationService = jasmine.createSpyObj<NotificationService>(
      'NotificationService',
      ['refresh', 'requestNotificationPermission', 'markAsRead', 'markAllAsRead'],
      {
        notifications$: of(notifications),
        unreadCount$: of(1),
        connectionStatus$: of(true),
      }
    );

    await TestBed.configureTestingModule({
      imports: [NotificationsComponent, NoopAnimationsModule],
      providers: [
        provideRouter([]),
        { provide: NotificationService, useValue: notificationService },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(NotificationsComponent);
    fixture.detectChanges();
  });

  it('renders notification center metrics from the stream', () => {
    const element: HTMLElement = fixture.nativeElement;

    expect(element.textContent).toContain('Уведомления');
    expect(element.textContent).toContain('1 непрочитано');
    expect(element.textContent).toContain('Заканчиваются чехлы');
    expect(element.textContent).toContain('Высокие');
  });

  it('marks a clicked notification as read and follows its action URL', () => {
    const router = TestBed.inject(Router);
    spyOn(router, 'navigateByUrl');

    fixture.nativeElement.querySelector('.notification-item').click();

    expect(notificationService.markAsRead).toHaveBeenCalledOnceWith(10);
    expect(router.navigateByUrl).toHaveBeenCalledOnceWith('/inventory');
  });
});
