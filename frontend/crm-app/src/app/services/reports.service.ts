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
  daily_revenue: Array<{
    date: string;
    revenue: number;
  }>;
}

@Injectable({
  providedIn: 'root'
})
export class ReportsService {
  constructor(private apiService: ApiService) {}

  getDashboardMetrics(): Observable<DashboardMetrics> {
    return this.apiService.get<DashboardMetrics>('/reports/dashboard-metrics');
  }

  getFinancialReport(
    dateFrom: string,
    dateTo: string,
    shopId?: number
  ): Observable<FinancialReport> {
    return this.apiService.get<FinancialReport>('/reports/financial', {
      date_from: dateFrom,
      date_to: dateTo,
      shop_id: shopId
    });
  }

  exportReport(
    reportType: string,
    format: 'pdf' | 'excel',
    params: Record<string, unknown>
  ): Observable<Blob> {
    return this.apiService.getBlob(`/reports/export/${reportType}`, {
      ...params,
      format
    });
  }

  exportDashboard(format: 'pdf' | 'excel', params: Record<string, unknown>): Observable<Blob> {
    return this.exportReport('dashboard', format, params);
  }
}
