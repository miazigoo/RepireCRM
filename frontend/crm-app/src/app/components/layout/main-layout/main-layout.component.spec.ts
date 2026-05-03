import { BreakpointObserver } from '@angular/cdk/layout';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatDialog } from '@angular/material/dialog';
import { By } from '@angular/platform-browser';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { provideRouter, RouterLink } from '@angular/router';
import { Store } from '@ngrx/store';
import { of } from 'rxjs';
import { NotificationService } from '../../../services/notification.service';
import { selectCurrentShop, selectCurrentUser } from '../../../store/auth/auth.selectors';
import { MainLayoutComponent } from './main-layout.component';

describe('MainLayoutComponent', () => {
  let fixture: ComponentFixture<MainLayoutComponent>;
  let store: jasmine.SpyObj<Store>;

  beforeEach(async () => {
    store = jasmine.createSpyObj<Store>('Store', ['select', 'dispatch']);
    store.select.and.callFake((selector: any) => {
      if (selector === selectCurrentUser) {
        return of({
          id: 1,
          username: 'b00bs',
          first_name: 'Test',
          last_name: 'User',
          is_director: true,
          role: { name: 'Директор' },
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
          provide: NotificationService,
          useValue: {
            notifications$: of([]),
            unreadCount$: of(0),
            connectionStatus$: of(true),
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
    expect(targets).toContain('/customers');
    expect(targets).toContain('/inventory');
    expect(targets).toContain('/reports');
    expect(targets).toContain('/admin');
    expect(targets).toContain('/admin/settings');
  });
});
