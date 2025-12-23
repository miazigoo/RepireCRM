import { Component, OnInit, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTabsModule } from '@angular/material/tabs';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { BaseChartDirective } from 'ng2-charts';
import { ChartConfiguration, ChartData, ChartType } from 'chart.js';
import { FormBuilder, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { ReportsService } from '../../../services/reports.service';
import { MatSnackBar } from '@angular/material/snack-bar';

interface DashboardMetrics {
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

@Component({
  selector: 'app-reports-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatTabsModule,
    MatDatepickerModule,
    MatFormFieldModule,
    MatSelectModule,
    BaseChartDirective
  ],
  templateUrl: './reports-dashboard.component.html',
  styleUrl: './reports-dashboard.component.css'
})
export class ReportsDashboardComponent implements OnInit {
  metrics: DashboardMetrics | null = null;
  filtersForm: FormGroup;
  loading = false;

  // Графики
  revenueChartData: ChartData<'line'> | null = null;
  servicesChartData: ChartData<'doughnut'> | null = null;
  performanceChartData: ChartData<'bar'> | null = null;

  revenueChartOptions: ChartConfiguration['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      title: {
        display: true,
        text: 'Динамика доходов'
      },
      legend: {
        position: 'top'
      }
    },
    scales: {
      y: {
        beginAtZero: true,
        ticks: {
          callback: function(value) {
            return new Intl.NumberFormat('ru-RU', {
              style: 'currency',
              currency: 'RUB',
              maximumFractionDigits: 0
            }).format(Number(value));
          }
        }
      }
    }
  };

  servicesChartOptions: ChartConfiguration['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      title: {
        display: true,
        text: 'Популярные услуги'
      },
      legend: {
        position: 'right'
      }
    }
  };

  performanceChartOptions: ChartConfiguration['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      title: {
        display: true,
        text: 'Производительность техников'
      }
    },
    scales: {
      y: {
        beginAtZero: true
      }
    }
  };

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
    this.loadMetrics();
    this.setupFilterChanges();
  }

  private setupFilterChanges(): void {
    this.filtersForm.valueChanges.subscribe(() => {
      this.loadMetrics();
    });
  }

  private loadMetrics(): void {
    this.loading = true;

    this.reportsService.getDashboardMetrics().subscribe({
      next: (metrics) => {
        this.metrics = metrics;
        this.setupCharts();
        this.loading = false;
      },
      error: (error) => {
        console.error('Error loading metrics:', error);
        this.snackBar.open('Ошибка загрузки метрик', 'Закрыть', { duration: 3000 });
        this.loading = false;
      }
    });
  }

  private setupCharts(): void {
    if (!this.metrics) return;

    // График доходов (будет загружаться отдельно с детальными данными)
    this.loadRevenueChart();

    // График услуг
    this.servicesChartData = {
      labels: this.metrics.top_services.map(s => s.name),
      datasets: [{
        data: this.metrics.top_services.map(s => s.revenue),
        backgroundColor: [
          '#FF6384',
          '#36A2EB',
          '#FFCE56',
          '#4BC0C0',
          '#9966FF',
          '#FF9F40'
        ]
      }]
    };

    // График производительности
    this.performanceChartData = {
      labels: this.metrics.technician_performance.map(t => t.name),
      datasets: [
        {
          label: 'Выполненных заказов',
          data: this.metrics.technician_performance.map(t => t.completed_orders),
          backgroundColor: '#36A2EB',
          yAxisID: 'y'
        },
        {
          label: 'Доход (тыс. руб.)',
          data: this.metrics.technician_performance.map(t => t.revenue / 1000),
          backgroundColor: '#FF6384',
          yAxisID: 'y1'
        }
      ]
    };
  }

  private loadRevenueChart(): void {
    // Здесь будет отдельный запрос для получения детальных данных по дням
    const filters = this.filtersForm.value;

    this.reportsService.getFinancialReport(
      filters.date_from || new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString(),
      filters.date_to || new Date().toISOString(),
      filters.shop_id
    ).subscribe({
      next: (report) => {
        this.revenueChartData = {
          labels: report.daily_revenue.map((item: any) =>
            new Date(item.date).toLocaleDateString('ru-RU')
          ),
          datasets: [{
            label: 'Доход',
            data: report.daily_revenue.map((item: any) => item.revenue),
            borderColor: '#36A2EB',
            backgroundColor: 'rgba(54, 162, 235, 0.1)',
            fill: true,
            tension: 0.4
          }]
        };
      },
      error: (error) => {
        console.error('Error loading revenue chart:', error);
      }
    });
  }

  exportReport(format: 'pdf' | 'excel'): void {
    if (!this.metrics) return;

    this.loading = true;

    // Здесь будет логика экспорта отчета
    this.reportsService.exportDashboard(format, this.filtersForm.value).subscribe({
      next: (blob) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `dashboard-report.${format}`;
        a.click();
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
    return '';
  }

  formatCurrency(value: number): string {
    return new Intl.NumberFormat('ru-RU', {
      style: 'currency',
      currency: 'RUB',
      maximumFractionDigits: 0
    }).format(value);
  }

  formatPercent(value: number): string {
    return `${value > 0 ? '+' : ''}${value.toFixed(1)}%`;
  }
}
