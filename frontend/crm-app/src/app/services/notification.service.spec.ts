import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { ApiService } from './api.service';
import { NotificationService, Notification } from './notification.service';

describe('NotificationService', () => {
  let service: NotificationService;
  let apiService: jasmine.SpyObj<ApiService>;

  const notifications: Notification[] = [
    {
      id: 1,
      title: 'Низкий остаток',
      message: 'Остался 1 чехол',
      priority: 'high',
      type: 'low_stock',
      icon: 'inventory_2',
      color: '#f59e0b',
      action_url: '/inventory',
      created_at: '2026-05-07T10:00:00Z',
      is_read: false,
    },
    {
      id: 2,
      title: 'Прочитано',
      message: 'Событие обработано',
      priority: 'normal',
      type: 'system',
      icon: 'notifications',
      color: 'primary',
      created_at: '2026-05-07T09:00:00Z',
      is_read: true,
    },
  ];

  beforeEach(() => {
    localStorage.setItem('access_token', 'token');
    apiService = jasmine.createSpyObj<ApiService>('ApiService', ['get', 'post']);
    apiService.get.and.returnValue(of(notifications));
    apiService.post.and.returnValue(of({ success: true }));

    TestBed.configureTestingModule({
      providers: [
        NotificationService,
        { provide: ApiService, useValue: apiService },
      ],
    });

    service = TestBed.inject(NotificationService);
  });

  afterEach(() => {
    localStorage.clear();
  });

  it('loads notifications through HTTP and tracks unread count', () => {
    let unreadCount = 0;
    let currentNotifications: Notification[] = [];

    service.unreadCount$.subscribe(count => unreadCount = count);
    service.notifications$.subscribe(items => currentNotifications = items);

    expect(apiService.get).toHaveBeenCalledWith('/notifications/', { limit: 20 });
    expect(currentNotifications.length).toBe(2);
    expect(unreadCount).toBe(1);
  });

  it('marks one notification as read through backend and local state', () => {
    let unreadCount = 0;
    let currentNotifications: Notification[] = [];
    service.unreadCount$.subscribe(count => unreadCount = count);
    service.notifications$.subscribe(items => currentNotifications = items);

    service.markAsRead(1);

    expect(apiService.post).toHaveBeenCalledOnceWith('/notifications/1/mark-read', {});
    expect(unreadCount).toBe(0);
    expect(currentNotifications.map(item => item.id)).toEqual([2]);
  });

  it('marks all notifications as read through backend and local state', () => {
    let unreadCount = 0;
    let currentNotifications: Notification[] = [];
    service.unreadCount$.subscribe(count => unreadCount = count);
    service.notifications$.subscribe(items => currentNotifications = items);

    service.markAllAsRead();

    expect(apiService.post).toHaveBeenCalledOnceWith('/notifications/mark-all-read', {});
    expect(unreadCount).toBe(0);
    expect(currentNotifications).toEqual([]);
  });
});
