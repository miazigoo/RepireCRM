import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';
import { SubscriptionPlan, SubscriptionStatus } from '../../../core/models/models';
import { AdminService } from '../../../services/admin.service';
import { AdminDashboardComponent } from './admin-dashboard.component';

describe('AdminDashboardComponent', () => {
  let fixture: ComponentFixture<AdminDashboardComponent>;
  let component: AdminDashboardComponent;
  let adminService: jasmine.SpyObj<AdminService>;

  const subscription = {
    organization_id: 1,
    organization_name: 'Main Repair',
    plan: {
      code: 'trial',
      name: 'Бесплатный период 45 дней',
      billing_period: 'trial',
      duration_days: 45,
      price: 0,
    },
    status: 'trial',
    status_display: 'Пробный период',
    started_at: '2026-05-02T00:00:00Z',
    expires_at: '2026-06-16T00:00:00Z',
    remaining_days: 45,
    remaining_percent: 100,
    color_bucket: 100,
    color_hex: '#1b8f3a',
    is_expired: false,
  } as SubscriptionStatus;

  const plans = [
    { code: 'trial', name: 'Бесплатный период 45 дней', price: 0 },
    { code: 'monthly', name: 'CRM на месяц', price: 1490 },
    { code: 'yearly', name: 'CRM на год', price: 14900 },
  ] as SubscriptionPlan[];

  beforeEach(async () => {
    adminService = jasmine.createSpyObj<AdminService>('AdminService', [
      'getSystemStatistics',
      'getSubscriptionStatus',
      'getSubscriptionPlans',
      'changeSubscription',
    ]);
    adminService.getSystemStatistics.and.returnValue(
      of({
        total_users: 2,
        active_users: 2,
        total_shops: 1,
        active_shops: 1,
        total_orders_today: 3,
        total_revenue_today: 12000,
        system_health: 'good',
      })
    );
    adminService.getSubscriptionStatus.and.returnValue(of(subscription));
    adminService.getSubscriptionPlans.and.returnValue(of(plans));

    await TestBed.configureTestingModule({
      imports: [AdminDashboardComponent],
      providers: [
        provideRouter([]),
        provideNoopAnimations(),
        { provide: AdminService, useValue: adminService },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(AdminDashboardComponent);
    component = fixture.componentInstance;
  });

  it('loads subscription and hides trial from paid plan actions', () => {
    fixture.detectChanges();

    expect(component.subscription).toEqual(subscription);
    expect(component.subscriptionLoading).toBeFalse();
    expect(component.subscriptionPlans.map((plan) => plan.code)).toEqual([
      'monthly',
      'yearly',
    ]);
  });

  it('renders redesigned admin shell with ruble formatting', () => {
    fixture.detectChanges();

    const element: HTMLElement = fixture.nativeElement;

    expect(element.querySelector('.admin-shell')).not.toBeNull();
    expect(element.textContent).toContain('Администрирование');
    expect(element.textContent).toContain('₽');
    expect(element.textContent).not.toContain('RUB');
    expect(component.formatCurrency(12000)).toContain('₽');
    expect(component.formatCurrency(12000)).not.toContain('RUB');
  });

  it('builds progress gradient from backend color and remaining percent', () => {
    component.subscription = {
      ...subscription,
      remaining_percent: 30,
      color_hex: '#ef842f',
    };

    expect(component.getSubscriptionGradient()).toBe(
      'linear-gradient(90deg, #ef842f 30%, #e5e7eb 0)'
    );
  });

  it('updates subscription after plan change', () => {
    const activeSubscription = {
      ...subscription,
      status: 'active',
      plan: { ...subscription.plan, code: 'yearly', name: 'CRM на год' },
    };
    adminService.changeSubscription.and.returnValue(of(activeSubscription));

    component.changeSubscription('yearly');

    expect(adminService.changeSubscription).toHaveBeenCalledOnceWith('yearly');
    expect(component.subscription).toEqual(activeSubscription);
    expect(component.subscriptionLoading).toBeFalse();
  });

  it('clears loading flag when plan change fails', () => {
    adminService.changeSubscription.and.returnValue(
      throwError(() => new Error('network'))
    );

    component.changeSubscription('yearly');

    expect(component.subscriptionLoading).toBeFalse();
  });
});
