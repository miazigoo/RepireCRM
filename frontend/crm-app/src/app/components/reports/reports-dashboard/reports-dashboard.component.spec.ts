import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MatSnackBar } from '@angular/material/snack-bar';
import { of } from 'rxjs';
import {
  DashboardMetrics,
  FinancialReport,
  ReportsService,
} from '../../../services/reports.service';
import { AuthService } from '../../../services/auth.service';
import { User } from '../../../core/models/models';
import { ReportsDashboardComponent } from './reports-dashboard.component';

describe('ReportsDashboardComponent', () => {
  let fixture: ComponentFixture<ReportsDashboardComponent>;
  let reportsService: jasmine.SpyObj<ReportsService>;
  let authUser: User;

  const metrics: DashboardMetrics = {
    period: { start_date: '2026-05-01', end_date: '2026-05-07', days: 7 },
    revenue: { current: 12000, previous: 8000, growth_percent: 50 },
    orders: { total: 4, completed: 3, in_progress: 1, conversion_rate: 75 },
    avg_check: { current: 4000 },
    top_services: [{ name: 'Замена стекла', count: 2, revenue: 7000 }],
    technician_performance: [{ name: 'Тест Мастер', completed_orders: 3, revenue: 12000 }],
  };

  const financialReport: FinancialReport = {
    summary: {
      total_revenue: 12000,
      total_orders: 3,
      avg_check: 4000,
      period_days: 7,
    },
    daily_revenue: [{ date: '2026-05-07', revenue: 12000 }],
    services_breakdown: [],
    shops_breakdown: [],
  };

  beforeEach(async () => {
    authUser = {
      id: 1,
      username: 'director',
      first_name: 'Главный',
      last_name: 'Директор',
      email: 'director@example.com',
      is_active: true,
      is_director: true,
      role: {
        id: 1,
        name: 'Директор',
        code: 'director',
        permission_codes: ['reports.view_all_shops'],
      },
    } as User;
    reportsService = jasmine.createSpyObj<ReportsService>('ReportsService', [
      'getDashboardMetrics',
      'getFinancialReport',
      'exportDashboard',
    ]);
    reportsService.getDashboardMetrics.and.returnValue(of(metrics));
    reportsService.getFinancialReport.and.returnValue(of(financialReport));
    reportsService.exportDashboard.and.returnValue(of(new Blob()));

    await TestBed.configureTestingModule({
      imports: [ReportsDashboardComponent, NoopAnimationsModule],
      providers: [
        { provide: ReportsService, useValue: reportsService },
        {
          provide: AuthService,
          useValue: {
            currentUser$: of(authUser),
            get currentUser() {
              return authUser;
            },
          },
        },
        { provide: MatSnackBar, useValue: { open: jasmine.createSpy('open') } },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(ReportsDashboardComponent);
    fixture.detectChanges();
  });

  it('loads dashboard metrics with the selected period filters', () => {
    expect(reportsService.getDashboardMetrics).toHaveBeenCalledWith(
      jasmine.objectContaining({
        period: '30_days',
      }),
    );
    expect(reportsService.getFinancialReport).toHaveBeenCalled();
    expect(fixture.componentInstance.metrics).toEqual(metrics);
  });

  it('passes all_shops to reports endpoints when global scope is selected', () => {
    reportsService.getDashboardMetrics.calls.reset();
    reportsService.getFinancialReport.calls.reset();

    fixture.componentInstance.setReportsScope(true);

    expect(reportsService.getDashboardMetrics).toHaveBeenCalledWith(
      jasmine.objectContaining({
        all_shops: true,
        shop_id: null,
      }),
    );
    expect(reportsService.getFinancialReport).toHaveBeenCalledWith(
      jasmine.any(String),
      jasmine.any(String),
      undefined,
      true,
    );
    expect(fixture.componentInstance.getScopeLabel()).toBe('Все филиалы');
  });

  it('formats money with the ruble sign instead of a currency code', () => {
    expect(fixture.componentInstance.formatCurrency(12000)).toContain('₽');
    expect(fixture.componentInstance.formatCurrency(12000)).not.toContain('RUB');
  });
});
