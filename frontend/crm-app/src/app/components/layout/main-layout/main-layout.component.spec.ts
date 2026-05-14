import { BreakpointObserver } from '@angular/cdk/layout';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatDialog } from '@angular/material/dialog';
import { By } from '@angular/platform-browser';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { provideRouter, Router, RouterLink } from '@angular/router';
import { Store } from '@ngrx/store';
import { of } from 'rxjs';
import { AuthService } from '../../../services/auth.service';
import { NotificationService } from '../../../services/notification.service';
import { OrdersService } from '../../../services/orders.service';
import { selectCurrentShop, selectCurrentUser } from '../../../store/auth/auth.selectors';
import { MainLayoutComponent } from './main-layout.component';

describe('MainLayoutComponent', () => {
  let fixture: ComponentFixture<MainLayoutComponent>;
  let store: jasmine.SpyObj<Store>;

  beforeEach(async () => {
    localStorage.removeItem('repaircrm.sidebarCollapsed');
    store = jasmine.createSpyObj<Store>('Store', ['select', 'dispatch']);
    store.select.and.callFake((selector: any) => {
      if (selector === selectCurrentUser) {
        return of({
          id: 1,
          username: 'b00bs',
          first_name: 'Test',
          last_name: 'User',
          is_director: true,
          avatar: 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw==',
          role: { name: 'Директор' },
          available_shops: [
            {
              id: 1,
              name: 'Ремонт+ Москва Центр',
              code: 'MSK01',
              is_active: true,
              timezone: 'Europe/Moscow',
              currency: 'RUB',
            },
          ],
        } as any);
      }

      if (selector === selectCurrentShop) {
        return of({
          id: 1,
          name: 'Ремонт+ Москва Центр',
          code: 'MSK01',
          is_active: true,
          timezone: 'Europe/Moscow',
          currency: 'RUB',
        } as any);
      }

      return of(null);
    });

    await TestBed.configureTestingModule({
      imports: [MainLayoutComponent, NoopAnimationsModule],
      providers: [
        provideRouter([]),
        { provide: Store, useValue: store },
        { provide: BreakpointObserver, useValue: { observe: () => of({ matches: false }) } },
        { provide: MatDialog, useValue: { open: jasmine.createSpy('open') } },
        {
          provide: AuthService,
          useValue: {
            getAvailableShops: jasmine.createSpy('getAvailableShops').and.returnValue(of([
              {
                id: 1,
                name: 'Ремонт+ Москва Центр',
                code: 'MSK01',
                is_active: true,
                timezone: 'Europe/Moscow',
                currency: 'RUB',
              },
            ])),
          },
        },
        {
          provide: OrdersService,
          useValue: {
            getOrdersPage: jasmine.createSpy('getOrdersPage').and.returnValue(of({
              items: [],
              count: 2,
              page: 1,
              page_size: 1,
              total_pages: 2,
            })),
          },
        },
        {
          provide: NotificationService,
          useValue: {
            notifications$: of([]),
            unreadCount$: of(0),
            connectionStatus$: of(true),
            refresh: jasmine.createSpy('refresh'),
            requestNotificationPermission: jasmine.createSpy('requestNotificationPermission'),
            markAsRead: jasmine.createSpy('markAsRead'),
            markAllAsRead: jasmine.createSpy('markAllAsRead'),
          },
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(MainLayoutComponent);
    fixture.detectChanges();
  });

  it('wires sidebar entries through Angular RouterLink directives', () => {
    const targets = fixture.debugElement
      .queryAll(By.directive(RouterLink))
      .map((debugElement) => debugElement.injector.get(RouterLink).urlTree!.toString());

    expect(targets).toContain('/dashboard');
    expect(targets).toContain('/orders');
    expect(targets).toContain('/tasks');
    expect(targets).toContain('/customers');
    expect(targets).toContain('/inventory');
    expect(targets).toContain('/services');
    expect(targets).toContain('/notifications');
    expect(targets).toContain('/reports');
    expect(targets).toContain('/admin');
    expect(targets).toContain('/admin/settings');
    expect(targets).toContain('/themes');
  });

  it('moves theme controls out of the top navbar and into the sidebar', () => {
    const element: HTMLElement = fixture.nativeElement;

    expect(element.querySelector('[aria-label="Переключить темную тему"]')).toBeNull();
    expect(element.querySelector('[aria-label="Выбрать тему"]')).toBeNull();
    expect(element.textContent).toContain('Темы');
  });

  it('does not highlight admin when system settings are active', () => {
    const router = TestBed.inject(Router);
    spyOnProperty(router, 'url', 'get').and.returnValue('/admin/settings');

    const systemItems = fixture.componentInstance.navigationGroups.find(group => group.label === 'Система')!.items;
    const adminItem = systemItems.find(item => item.label === 'Администрирование')!;
    const settingsItem = systemItems.find(item => item.label === 'Настройки')!;

    expect(fixture.componentInstance.isNavigationItemActive(adminItem)).toBeFalse();
    expect(fixture.componentInstance.isNavigationItemActive(settingsItem)).toBeTrue();
  });

  it('uses real unread notification count in navigation badges', () => {
    expect(fixture.componentInstance.notificationsCount).toBe(0);

    const notificationItem = fixture.componentInstance.navigationGroups
      .flatMap(group => group.items)
      .find(item => item.label === 'Уведомления')!;

    expect(fixture.componentInstance.getBadgeValue(notificationItem)).toBe(0);
  });

  it('shows the current shop once in the workspace switcher', () => {
    const element: HTMLElement = fixture.nativeElement;

    expect(element.querySelector('.shop-select')).toBeNull();
    expect(element.querySelectorAll('.workspace-title').length).toBe(1);
    expect(element.querySelector('.workspace-title')?.textContent?.trim()).toBe('Ремонт+ Москва Центр');
  });

  it('formats shop switcher metadata without merging the branch name and code', () => {
    expect(fixture.componentInstance.getShopMeta({
      id: 2,
      name: 'Repair CRM Екатеринбург',
      code: 'EKB01',
      city: 'Екатеринбург',
      is_active: true,
      timezone: 'Europe/Moscow',
      currency: 'RUB',
    })).toBe('Екатеринбург · EKB01');
    expect(fixture.componentInstance.getShopCountLabel(1)).toBe('точка');
    expect(fixture.componentInstance.getShopCountLabel(3)).toBe('точки');
    expect(fixture.componentInstance.getShopCountLabel(5)).toBe('точек');
  });

  it('collapses the desktop sidebar from the header control', () => {
    fixture.componentInstance.toggleSidebar();
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('.sidenav.collapsed')).toBeTruthy();
    expect(localStorage.getItem('repaircrm.sidebarCollapsed')).toBe('true');
  });

  it('renders the current user avatar in the account card', () => {
    const image = fixture.nativeElement.querySelector('.profile-avatar img') as HTMLImageElement;

    expect(image).toBeTruthy();
    expect(image.getAttribute('src')).toBe('data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw==');
  });

  it('falls back to user initials if the avatar cannot be loaded', () => {
    fixture.componentInstance.onProfileAvatarError();
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('.profile-avatar img')).toBeNull();
    expect(fixture.nativeElement.querySelector('.profile-avatar')?.textContent?.trim()).toBe('TU');
  });
});
