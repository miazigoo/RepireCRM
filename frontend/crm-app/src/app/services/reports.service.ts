import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';

export interface DashboardMetrics {
  period: {
    start_date: string;
    end_date: string;
    days: number;
  };
  revenue: {
    current: number;
    previous: number;
    growth_percent: number;
  };
  orders: {
    total: number;
    completed: number;
    in_progress: number;
    conversion_rate: number;
  };
  avg_check: {
    current: number;
  };
  top_services: Array<{
    name: string;
    count: number;
    revenue: number;
  }>;
  technician_performance: Array<{
    name: string;
    completed_orders: number;
    revenue: number;
  }>;
}

export interface FinancialReport {
  summary: {
    total_revenue: number;
    total_orders: number;
    avg_check: number;
    period_days: number;
  };
  daily_revenue: Array<{
    date: string;
    revenue: number;
  }>;
  services_breakdown: Array<{
    service: string;
    revenue: number;
    count: number;
  }>;
  shops_breakdown: Array<{
    shop: string;
    revenue: number;
    orders: number;
  }>;
}

@Injectable({
  providedIn: 'root'
})
export class ReportsService {
  constructor(private apiService: ApiService) {}

  getDashboardMetrics(params?: Record<string, unknown>): Observable<DashboardMetrics> {
    const cleanedParams = this.cleanParams(params);

    if (Object.keys(cleanedParams).length === 0) {
      return this.apiService.get<DashboardMetrics>('/reports/dashboard-metrics');
    }

    return this.apiService.get<DashboardMetrics>('/reports/dashboard-metrics', cleanedParams);
  }

  getFinancialReport(
    dateFrom: string,
    dateTo: string,
    shopId?: number
  ): Observable<FinancialReport> {
    return this.apiService.get<FinancialReport>('/reports/financial', this.cleanParams({
      date_from: dateFrom,
      date_to: dateTo,
      shop_id: shopId
    }));
  }

  exportReport(
    reportType: string,
    format: 'pdf' | 'excel',
    params: Record<string, unknown>
  ): Observable<Blob> {
    return this.apiService.getBlob(`/reports/export/${reportType}`, this.cleanParams({
      ...params,
      format
    }));
  }

  exportDashboard(format: 'pdf' | 'excel', params: Record<string, unknown>): Observable<Blob> {
    return this.exportReport('dashboard', format, params);
  }

  private cleanParams(params?: Record<string, unknown>): Record<string, unknown> {
    return Object.entries(params || {}).reduce<Record<string, unknown>>((result, [key, value]) => {
      if (value !== null && value !== undefined && value !== '') {
        result[key] = value;
      }
      return result;
    }, {});
  }
}
