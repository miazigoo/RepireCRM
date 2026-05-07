import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';
import { catchError, map } from 'rxjs/operators';
import { ApiService } from './api.service';

export interface FinancialSummary {
  total_income: number;
  total_expenses: number;
  net_profit: number;
  cash_balance: number;
  pending_payments: number;
  profit_margin: number;
}

export interface RecentTransaction {
  id: number;
  type: 'income' | 'expense';
  amount: number;
  description: string;
  date: string;
  status: 'completed' | 'pending' | 'cancelled';
  payment_method: string;
}

export interface ProfitChart {
  labels: string[];
  income: number[];
  expenses: number[];
  profit: number[];
}

export interface ExpensesBreakdown {
  categories: string[];
  amounts: number[];
}

interface FinancialReport {
  summary: {
    total_revenue: number;
    total_orders: number;
    avg_check: number;
    period_days: number;
  };
  daily_revenue: Array<{ date: string; revenue: number }>;
  services_breakdown: Array<{ service: string; revenue: number; count: number }>;
  shops_breakdown: Array<{ shop: string; revenue: number; orders: number }>;
}

@Injectable({
  providedIn: 'root'
})
export class FinanceService {
  constructor(private apiService: ApiService) {}

  getFinancialSummary(filters: Record<string, unknown>): Observable<FinancialSummary> {
    return this.getFinancialReport(filters).pipe(
      map((report) => ({
        total_income: report.summary.total_revenue,
        total_expenses: 0,
        net_profit: report.summary.total_revenue,
        cash_balance: report.summary.total_revenue,
        pending_payments: 0,
        profit_margin: report.summary.total_revenue > 0 ? 100 : 0
      })),
      catchError(() => of({
        total_income: 0,
        total_expenses: 0,
        net_profit: 0,
        cash_balance: 0,
        pending_payments: 0,
        profit_margin: 0
      }))
    );
  }

  getRecentTransactions(): Observable<RecentTransaction[]> {
    return of([]);
  }

  getProfitChart(filters: Record<string, unknown>): Observable<ProfitChart> {
    return this.getFinancialReport(filters).pipe(
      map((report) => ({
        labels: report.daily_revenue.map((item) => this.formatChartDate(item.date)),
        income: report.daily_revenue.map((item) => item.revenue),
        expenses: report.daily_revenue.map(() => 0),
        profit: report.daily_revenue.map((item) => item.revenue)
      })),
      catchError(() => of({ labels: [], income: [], expenses: [], profit: [] }))
    );
  }

  getExpensesBreakdown(filters: Record<string, unknown>): Observable<ExpensesBreakdown> {
    return this.getFinancialReport(filters).pipe(
      map((report) => {
        const rows = report.services_breakdown.length
          ? report.services_breakdown
          : [{ service: 'Выручка', revenue: report.summary.total_revenue, count: report.summary.total_orders }];

        return {
          categories: rows.map((item) => item.service),
          amounts: rows.map((item) => item.revenue)
        };
      }),
      catchError(() => of({ categories: ['Нет данных'], amounts: [0] }))
    );
  }

  exportFinancialReport(filters: Record<string, unknown>): Observable<Blob> {
    return this.getFinancialReport(filters).pipe(
      map((report) => {
        const lines = [
          'Финансовый отчет',
          `Выручка: ${report.summary.total_revenue}`,
          `Заказы: ${report.summary.total_orders}`,
          `Средний чек: ${report.summary.avg_check}`,
          '',
          'Динамика по дням:',
          ...report.daily_revenue.map((item) => `${item.date};${item.revenue}`),
          '',
          'Услуги:',
          ...report.services_breakdown.map((item) => `${item.service};${item.count};${item.revenue}`)
        ];

        return new Blob([lines.join('\n')], {
          type: 'text/plain;charset=utf-8'
        });
      })
    );
  }

  private getFinancialReport(filters: Record<string, unknown>): Observable<FinancialReport> {
    return this.apiService.get<FinancialReport>('/reports/financial', this.buildReportFilters(filters));
  }

  private buildReportFilters(filters: Record<string, unknown>): Record<string, string> {
    const period = String(filters['period'] || '30_days');
    const now = new Date();
    const dateTo = this.toDate(filters['date_to']) ?? now;
    const dateFrom = this.toDate(filters['date_from']) ?? this.getPeriodStart(period, dateTo);

    return {
      date_from: dateFrom.toISOString(),
      date_to: dateTo.toISOString()
    };
  }

  private toDate(value: unknown): Date | null {
    if (!value) {
      return null;
    }

    if (value instanceof Date) {
      return value;
    }

    const parsed = new Date(String(value));
    return Number.isNaN(parsed.getTime()) ? null : parsed;
  }

  private getPeriodStart(period: string, dateTo: Date): Date {
    const daysByPeriod: Record<string, number> = {
      '7_days': 6,
      '30_days': 29,
      '90_days': 89
    };
    const days = daysByPeriod[period] ?? 29;
    const date = new Date(dateTo);
    date.setDate(date.getDate() - days);
    return date;
  }

  private formatChartDate(value: string): string {
    return new Intl.DateTimeFormat('ru-RU', {
      day: '2-digit',
      month: '2-digit'
    }).format(new Date(value));
  }
}
