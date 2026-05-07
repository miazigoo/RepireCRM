import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTabsModule } from '@angular/material/tabs';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { provideNativeDateAdapter } from '@angular/material/core';
import { BaseChartDirective } from 'ng2-charts';
import { ChartConfiguration, ChartData } from 'chart.js';
import { FormBuilder, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { MatSnackBar } from '@angular/material/snack-bar';
import {
  DashboardMetrics,
  FinancialReport,
  ReportsService
} from '../../../services/reports.service';
import { ensureChartComponentsRegistered } from '../../../core/charts/register-chart-components';

ensureChartComponentsRegistered();

interface ReportPeriodOption {
  value: string;
  label: string;
  hint: string;
}

interface ChartPalette {
  text: string;
  muted: string;
  grid: string;
  primary: string;
  accent: string;
  success: string;
  warning: string;
  danger: string;
  surface: string;
}

interface ReportFilterParams extends Record<string, unknown> {
  period: string;
  date_from: string | null;
  date_to: string | null;
  shop_id: number | null;
}

@Component({
  selector: 'app-reports-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatButtonModule,
    MatIconModule,
    MatTabsModule,
    MatDatepickerModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatProgressSpinnerModule,
    BaseChartDirective
  ],
  providers: [provideNativeDateAdapter()],
  templateUrl: './reports-dashboard.component.html',
  styleUrl: './reports-dashboard.component.scss'
})
export class ReportsDashboardComponent implements OnInit {
  readonly periodOptions: ReportPeriodOption[] = [
    { value: 'today', label: 'Сегодня', hint: 'Текущий день' },
    { value: '7_days', label: '7 дней', hint: 'Неделя' },
    { value: '30_days', label: '30 дней', hint: 'Месяц' },
    { value: '90_days', label: '90 дней', hint: 'Квартал' },
    { value: 'month', label: 'Этот месяц', hint: 'С начала месяца' },
    { value: 'custom', label: 'Свой период', hint: 'Ручной диапазон' }
  ];

  metrics: DashboardMetrics | null = null;
  financialSummary: FinancialReport['summary'] | null = null;
  filtersForm: FormGroup;
  loading = false;
  chartLoading = false;
  lastUpdated: Date | null = null;

  revenueChartData: ChartData<'line'> | null = null;
  servicesChartData: ChartData<'doughnut'> | null = null;
  performanceChartData: ChartData<'bar'> | null = null;

  revenueChartOptions: ChartConfiguration<'line'>['options'] = {};
  servicesChartOptions: ChartConfiguration<'doughnut'>['options'] = {};
  performanceChartOptions: ChartConfiguration<'bar'>['options'] = {};

  constructor(
    private fb: FormBuilder,
    private reportsService: ReportsService,
    private snackBar: MatSnackBar
  ) {
    this.filtersForm = this.fb.group({
      period: ['30_days'],
      date_from: [null],
      date_to: [null],
      shop_id: [null]
    });
  }

  ngOnInit(): void {
    this.applyPresetPeriod('30_days', false);
    this.loadMetrics();

    this.filtersForm.get('period')?.valueChanges.subscribe(period => {
      if (period && period !== 'custom') {
        this.applyPresetPeriod(period);
      }
    });
  }

  applyFilters(): void {
    this.loadMetrics();
  }

  onCustomDateChange(): void {
    this.filtersForm.patchValue({ period: 'custom' }, { emitEvent: false });
  }

  exportReport(format: 'pdf' | 'excel'): void {
    if (!this.metrics) return;

    this.loading = true;

    this.reportsService.exportDashboard(format, this.getFilterParams()).subscribe({
      next: (blob) => {
        const url = window.URL.createObjectURL(blob);
        const anchor = document.createElement('a');
        anchor.href = url;
        anchor.download = `dashboard-report.${format === 'excel' ? 'csv' : 'pdf'}`;
        anchor.click();
        window.URL.revokeObjectURL(url);

        this.loading = false;
        this.snackBar.open('Отчет экспортирован', 'Закрыть', { duration: 3000 });
      },
      error: (error) => {
        console.error('Error exporting report:', error);
        this.snackBar.open('Ошибка экспорта отчета', 'Закрыть', { duration: 3000 });
        this.loading = false;
      }
    });
  }

  getGrowthIcon(): string {
    if (!this.metrics) return 'trending_flat';

    const growth = this.metrics.revenue.growth_percent;
    if (growth > 0) return 'trending_up';
    if (growth < 0) return 'trending_down';
    return 'trending_flat';
  }

  getGrowthColor(): string {
    if (!this.metrics) return '';

    const growth = this.metrics.revenue.growth_percent;
    if (growth > 0) return 'success';
    if (growth < 0) return 'warn';
    return 'neutral';
  }

  getPeriodLabel(): string {
    const period = this.filtersForm.get('period')?.value;
    return this.periodOptions.find(option => option.value === period)?.label || 'Период';
  }

  getDateRangeLabel(): string {
    const { date_from: dateFrom, date_to: dateTo } = this.filtersForm.value;

    if (!dateFrom || !dateTo) {
      return 'Диапазон не выбран';
    }

    return `${this.formatShortDate(dateFrom)} - ${this.formatShortDate(dateTo)}`;
  }

  getCompletionRate(): number {
    if (!this.metrics || this.metrics.orders.total === 0) {
      return 0;
    }

    return Math.round((this.metrics.orders.completed / this.metrics.orders.total) * 100);
  }

  getAverageCheckDelta(): number {
    if (!this.metrics || this.metrics.revenue.previous <= 0) {
      return 0;
    }

    return this.metrics.avg_check.current / this.metrics.revenue.previous * 100;
  }

  formatCurrency(value: number | null | undefined): string {
    return `${new Intl.NumberFormat('ru-RU', {
      maximumFractionDigits: 0
    }).format(value || 0)} ₽`;
  }

  formatNumber(value: number | null | undefined): string {
    return new Intl.NumberFormat('ru-RU', {
      maximumFractionDigits: 0
    }).format(value || 0);
  }

  formatPercent(value: number | null | undefined): string {
    const numericValue = value || 0;
    return `${numericValue > 0 ? '+' : ''}${numericValue.toFixed(1)}%`;
  }

  private loadMetrics(): void {
    this.loading = true;
    this.configureChartOptions();

    this.reportsService.getDashboardMetrics(this.getFilterParams()).subscribe({
      next: (metrics) => {
        this.metrics = metrics;
        this.setupCharts();
        this.lastUpdated = new Date();
        this.loading = false;
      },
      error: (error) => {
        console.error('Error loading metrics:', error);
        this.snackBar.open('Ошибка загрузки метрик', 'Закрыть', { duration: 3000 });
        this.loading = false;
        this.chartLoading = false;
      }
    });
  }

  private setupCharts(): void {
    if (!this.metrics) return;

    const palette = this.getChartPalette();
    this.loadRevenueChart(palette);
    this.setupServicesChart(palette);
    this.setupPerformanceChart(palette);
  }

  private setupServicesChart(palette: ChartPalette): void {
    if (!this.metrics?.top_services.length) {
      this.servicesChartData = null;
      return;
    }

    this.servicesChartData = {
      labels: this.metrics.top_services.map(service => service.name),
      datasets: [{
        data: this.metrics.top_services.map(service => service.revenue),
        backgroundColor: [
          palette.primary,
          palette.accent,
          palette.success,
          palette.warning,
          palette.danger
        ],
        borderColor: palette.surface,
        borderWidth: 3,
        hoverOffset: 8
      }]
    };
  }

  private setupPerformanceChart(palette: ChartPalette): void {
    if (!this.metrics?.technician_performance.length) {
      this.performanceChartData = null;
      return;
    }

    this.performanceChartData = {
      labels: this.metrics.technician_performance.map(technician => technician.name.trim() || 'Без имени'),
      datasets: [
        {
          label: 'Заказы',
          data: this.metrics.technician_performance.map(technician => technician.completed_orders),
          backgroundColor: palette.primary,
          borderRadius: 8,
          yAxisID: 'y'
        },
        {
          label: 'Выручка, тыс. ₽',
          data: this.metrics.technician_performance.map(technician => technician.revenue / 1000),
          backgroundColor: palette.accent,
          borderRadius: 8,
          yAxisID: 'y1'
        }
      ]
    };
  }

  private loadRevenueChart(palette: ChartPalette): void {
    this.chartLoading = true;
    const params = this.getFilterParams();

    this.reportsService.getFinancialReport(
      params.date_from as string,
      params.date_to as string,
      params.shop_id || undefined
    ).subscribe({
      next: (report) => {
        this.financialSummary = report.summary;
        this.revenueChartData = report.daily_revenue.length ? {
          labels: report.daily_revenue.map(item => new Date(item.date).toLocaleDateString('ru-RU', {
            day: '2-digit',
            month: 'short'
          })),
          datasets: [{
            label: 'Выручка',
            data: report.daily_revenue.map(item => item.revenue),
            borderColor: palette.primary,
            backgroundColor: this.withAlpha(palette.primary, 0.14),
            pointBackgroundColor: palette.primary,
            pointBorderColor: palette.surface,
            pointHoverRadius: 5,
            fill: true,
            tension: 0.38
          }]
        } : null;
        this.chartLoading = false;
      },
      error: (error) => {
        console.error('Error loading revenue chart:', error);
        this.revenueChartData = null;
        this.chartLoading = false;
      }
    });
  }

  private configureChartOptions(): void {
    const palette = this.getChartPalette();
    const moneyTick = (value: string | number) => this.formatCurrency(Number(value));

    this.revenueChartOptions = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: false,
          labels: { color: palette.text }
        },
        tooltip: {
          callbacks: {
            label: context => ` ${this.formatCurrency(Number(context.parsed.y || 0))}`
          }
        }
      },
      scales: {
        x: {
          ticks: { color: palette.muted },
          grid: { color: palette.grid }
        },
        y: {
          beginAtZero: true,
          ticks: {
            color: palette.muted,
            callback: moneyTick
          },
          grid: { color: palette.grid }
        }
      }
    };

    this.servicesChartOptions = {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '68%',
      plugins: {
        legend: {
          position: 'bottom',
          labels: {
            color: palette.text,
            boxWidth: 10,
            boxHeight: 10,
            usePointStyle: true
          }
        },
        tooltip: {
          callbacks: {
            label: context => ` ${context.label}: ${this.formatCurrency(Number(context.parsed || 0))}`
          }
        }
      }
    };

    this.performanceChartOptions = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'top',
          labels: { color: palette.text }
        }
      },
      scales: {
        x: {
          ticks: { color: palette.muted },
          grid: { display: false }
        },
        y: {
          beginAtZero: true,
          ticks: { color: palette.muted },
          grid: { color: palette.grid }
        },
        y1: {
          beginAtZero: true,
          position: 'right',
          ticks: { color: palette.muted },
          grid: { drawOnChartArea: false }
        }
      }
    };
  }

  private applyPresetPeriod(period: string, shouldLoad = true): void {
    const { start, end } = this.getPresetRange(period);
    this.filtersForm.patchValue({
      period,
      date_from: start,
      date_to: end
    }, { emitEvent: false });

    if (shouldLoad) {
      this.loadMetrics();
    }
  }

  private getPresetRange(period: string): { start: Date; end: Date } {
    const end = new Date();
    const start = new Date(end);

    if (period === 'today') {
      start.setHours(0, 0, 0, 0);
      return { start, end };
    }

    if (period === '7_days') {
      start.setDate(end.getDate() - 6);
    } else if (period === '90_days') {
      start.setDate(end.getDate() - 89);
    } else if (period === 'month') {
      start.setDate(1);
    } else {
      start.setDate(end.getDate() - 29);
    }

    start.setHours(0, 0, 0, 0);
    return { start, end };
  }

  private getFilterParams(): ReportFilterParams {
    const filters = this.filtersForm.value;

    return {
      period: filters.period || '30_days',
      date_from: this.toApiDate(filters.date_from, false),
      date_to: this.toApiDate(filters.date_to, true),
      shop_id: filters.shop_id
    };
  }

  private toApiDate(value: Date | string | null, endOfDay: boolean): string | null {
    if (!value) {
      return null;
    }

    const date = value instanceof Date ? new Date(value) : new Date(value);
    if (endOfDay) {
      date.setHours(23, 59, 59, 999);
    } else {
      date.setHours(0, 0, 0, 0);
    }

    return date.toISOString();
  }

  private formatShortDate(value: Date | string): string {
    return new Date(value).toLocaleDateString('ru-RU', {
      day: '2-digit',
      month: 'short'
    });
  }

  private getChartPalette(): ChartPalette {
    const styles = getComputedStyle(document.body);
    const read = (name: string, fallback: string) => styles.getPropertyValue(name).trim() || fallback;

    return {
      text: read('--color-text-primary', '#111827'),
      muted: read('--color-text-secondary', '#64748b'),
      grid: this.withAlpha(read('--color-border', '#d8e0ea'), 0.7),
      primary: read('--color-primary', '#2563eb'),
      accent: read('--color-accent', '#0f766e'),
      success: read('--color-success', '#15803d'),
      warning: read('--color-warning', '#b45309'),
      danger: read('--color-danger', '#b91c1c'),
      surface: read('--panel-background', '#ffffff')
    };
  }

  private withAlpha(color: string, alpha: number): string {
    if (color.startsWith('#')) {
      const hex = color.replace('#', '');
      const value = hex.length === 3
        ? hex.split('').map(part => part + part).join('')
        : hex;
      const red = parseInt(value.slice(0, 2), 16);
      const green = parseInt(value.slice(2, 4), 16);
      const blue = parseInt(value.slice(4, 6), 16);
      return `rgba(${red}, ${green}, ${blue}, ${alpha})`;
    }

    return color;
  }
}
