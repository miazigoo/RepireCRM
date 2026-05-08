import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { SubscriptionPlan, SubscriptionStatus } from '../core/models/models';
import { ApiService } from './api.service';
import { AdminService } from './admin.service';

describe('AdminService', () => {
  let service: AdminService;
  let apiService: jasmine.SpyObj<ApiService>;

  beforeEach(() => {
    apiService = jasmine.createSpyObj<ApiService>('ApiService', ['get', 'post']);

    TestBed.configureTestingModule({
      providers: [AdminService, { provide: ApiService, useValue: apiService }],
    });

    service = TestBed.inject(AdminService);
  });

  it('loads current subscription status from shops API', () => {
    const status = {
      organization_id: 1,
      organization_name: 'Main',
      status: 'trial',
      remaining_days: 45,
      remaining_percent: 100,
      color_bucket: 100,
      color_hex: '#1b8f3a',
    } as SubscriptionStatus;
    apiService.get.and.returnValue(of(status));

    service.getSubscriptionStatus().subscribe((result) => {
      expect(result).toEqual(status);
    });

    expect(apiService.get).toHaveBeenCalledOnceWith('/shops/subscription/status');
  });

  it('loads subscription plans from shops API', () => {
    const plans = [{ code: 'monthly', name: 'CRM на месяц', price: 1490 }] as SubscriptionPlan[];
    apiService.get.and.returnValue(of(plans));

    service.getSubscriptionPlans().subscribe((result) => {
      expect(result).toEqual(plans);
    });

    expect(apiService.get).toHaveBeenCalledOnceWith('/shops/subscription/plans');
  });

  it('loads system statistics from admin API', () => {
    const stats = {
      total_users: 3,
      active_users: 2,
      total_shops: 1,
      active_shops: 1,
      total_orders_today: 5,
      total_revenue_today: 14000,
      system_health: 'good',
    };
    apiService.get.and.returnValue(of(stats));

    service.getSystemStatistics().subscribe((result) => {
      expect(result).toEqual(stats);
    });

    expect(apiService.get).toHaveBeenCalledOnceWith('/admin/statistics');
  });

  it('loads global system statistics when requested', () => {
    const stats = {
      total_users: 6,
      active_users: 5,
      total_shops: 3,
      active_shops: 3,
      total_orders_today: 9,
      total_revenue_today: 34000,
      system_health: 'good',
    };
    apiService.get.and.returnValue(of(stats));

    service.getSystemStatistics(true).subscribe((result) => {
      expect(result).toEqual(stats);
    });

    expect(apiService.get).toHaveBeenCalledOnceWith('/admin/statistics', {
      all_shops: true,
    });
  });

  it('changes subscription using backend plan_code contract', () => {
    const status = { status: 'active', plan: { code: 'yearly' } } as SubscriptionStatus;
    apiService.post.and.returnValue(of(status));

    service.changeSubscription('yearly').subscribe((result) => {
      expect(result).toEqual(status);
    });

    expect(apiService.post).toHaveBeenCalledOnceWith('/shops/subscription/change', {
      plan_code: 'yearly',
    });
  });
});
