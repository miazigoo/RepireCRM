import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { ApiService } from './api.service';
import { DashboardMetrics, ReportsService } from './reports.service';

describe('ReportsService', () => {
  let service: ReportsService;
  let apiService: jasmine.SpyObj<ApiService>;

  beforeEach(() => {
    apiService = jasmine.createSpyObj<ApiService>('ApiService', ['get', 'getBlob']);

    TestBed.configureTestingModule({
      providers: [
        ReportsService,
        { provide: ApiService, useValue: apiService },
      ],
    });

    service = TestBed.inject(ReportsService);
  });

  it('loads dashboard metrics from the backend reports route', () => {
    const metrics = {
      period: { start_date: '2026-05-01', end_date: '2026-05-31', days: 30 },
      revenue: { current: 0, previous: 0, growth_percent: 0 },
      orders: { total: 0, completed: 0, in_progress: 0, conversion_rate: 0 },
      avg_check: { current: 0 },
      top_services: [],
      technician_performance: [],
    } as DashboardMetrics;
    apiService.get.and.returnValue(of(metrics));

    service.getDashboardMetrics().subscribe((result) => {
      expect(result).toEqual(metrics);
    });

    expect(apiService.get).toHaveBeenCalledOnceWith('/reports/dashboard-metrics');
  });
});
