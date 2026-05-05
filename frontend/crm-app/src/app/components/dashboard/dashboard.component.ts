import { Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { merge, Subject, takeUntil } from 'rxjs';
import { OrdersService } from '../../services/orders.service';
import { Order } from '../../core/models/models';
import { BaseChartDirective } from 'ng2-charts';
import { ChartConfiguration, ChartData } from 'chart.js';
import { RouterModule } from '@angular/router';
import { ensureChartComponentsRegistered } from '../../core/charts/register-chart-components';
import { ThemeService } from '../../services/theme.service';

ensureChartComponentsRegistered();

interface DashboardStats {
  total_orders: number;
  total_revenue: number;
  avg_order_value: number;
  recent_orders: number;
  recent_revenue: number;
  status_distribution: Array<{status: string, count: number}>;
}

interface StatusRow {
  status: string;
  label: string;
  count: number;
  percent: number;
  color: string;
}

interface QuickAction {
  title: string;
  caption: string;
  icon: string;
  route: string;
  tone: 'primary' | 'accent' | 'success' | 'warning';
  queryParams?: Record<string, string>;
}

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    MatIconModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    BaseChartDirective
  ],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.scss'
})
export class DashboardComponent implements OnInit, OnDestroy {
  stats: DashboardStats | null = null;
  recentOrders: Order[] = [];
  statusRows: StatusRow[] = [];
  isLoadingStats = true;
  isLoadingOrders = true;
  statsError = '';
  ordersError = '';

  readonly quickActions: QuickAction[] = [
    {
      title: 'Новый заказ',
      caption: 'Приемка устройства',
      icon: 'add',
      route: '/orders/new',
      tone: 'primary'
    },
    {
      title: 'Новый клиент',
      caption: 'Карточка клиента',
      icon: 'person_add',
      route: '/customers/new',
      tone: 'accent'
    },
    {
      title: 'Заказ поставщику',
      caption: 'Пополнить склад',
      icon: 'local_shipping',
      route: '/inventory/purchase-orders/new',
      tone: 'warning'
    },
    {
      title: 'Готовые заказы',
      caption: 'К выдаче клиентам',
      icon: 'check_circle',
      route: '/orders',
      tone: 'success',
      queryParams: { status: 'ready' }
    }
  ];

  chartType: 'doughnut' = 'doughnut';
  chartData: ChartData<'doughnut'> | null = null;
  chartOptions: ChartConfiguration<'doughnut'>['options'] = this.buildChartOptions();

  private readonly moneyFormatter = new Intl.NumberFormat('ru-RU', {
    maximumFractionDigits: 0
  });
  private readonly statusLabels: Record<string, string> = {
    'received': 'Принят',
    'diagnosed': 'Диагностика',
    'waiting_parts': 'Ожидает запчасти',
    'in_repair': 'В ремонте',
    'testing': 'Тестирование',
    'ready': 'Готов',
    'completed': 'Выдан',
    'cancelled': 'Отменен'
  };
  private readonly statusColors: Record<string, string> = {
    'received': '#2563eb',
    'diagnosed': '#f59e0b',
    'waiting_parts': '#8b5cf6',
    'in_repair': '#f97316',
    'testing': '#06b6d4',
    'ready': '#16a34a',
    'completed': '#14b8a6',
    'cancelled': '#ef4444'
  };
  private readonly destroy$ = new Subject<void>();

  constructor(
    private ordersService: OrdersService,
    private themeService: ThemeService
  ) {}

  ngOnInit(): void {
    this.watchThemeChanges();
    this.loadDashboardData();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  get dashboardSubtitle(): string {
    if (this.isLoadingStats) {
      return 'Загружаем оперативную сводку сервиса';
    }

    if (!this.stats || this.stats.total_orders === 0) {
      return 'Нет заказов в выбранной точке, можно начать с новой приемки';
    }

    return `${this.stats.recent_orders} за 30 дней, ${this.activeOrdersCount} в активной работе`;
  }

  get activeOrdersCount(): number {
    return this.getStatusCount(['received', 'diagnosed', 'waiting_parts', 'in_repair', 'testing']);
  }

  get readyOrdersCount(): number {
    return this.getStatusCount(['ready']);
  }

  get completedOrdersCount(): number {
    return this.getStatusCount(['completed']);
  }

  getRecentOrdersShare(): string {
    const total = this.stats?.total_orders || 0;
    if (!total) {
      return 'пока нет истории';
    }
    const share = ((this.stats?.recent_orders || 0) / total) * 100;
    return `${share.toFixed(1)}% от базы`;
  }

  getStatusLabel(status: string): string {
    return this.statusLabels[status] || status;
  }

  getStatusColor(status: string): string {
    return this.statusColors[status] || '#64748b';
  }

  getOrderAmount(order: Order): number {
    return Number(order.final_cost || order.cost_estimate || order.total_cost || 0);
  }

  getCustomerName(order: Order): string {
    const customer = order.customer;
    const name = [customer?.last_name, customer?.first_name].filter(Boolean).join(' ');
    return name || 'Клиент без имени';
  }

  getDeviceName(order: Order): string {
    const model = order.device?.model;
    const brand = model?.brand?.name;
    const name = model?.name;
    return [brand, name].filter(Boolean).join(' ') || 'Устройство не указано';
  }

  formatMoney(value: number | null | undefined): string {
    return `${this.moneyFormatter.format(Number(value || 0))} ₽`;
  }

  private loadDashboardData(): void {
    this.isLoadingStats = true;
    this.statsError = '';
    this.ordersService.getStatistics()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: stats => {
          this.stats = this.normalizeStats(stats);
          this.setupStatusRows(this.stats.status_distribution);
          this.isLoadingStats = false;
        },
        error: () => {
          this.stats = this.normalizeStats(null);
          this.statusRows = [];
          this.chartData = null;
          this.statsError = 'Статистика временно недоступна';
          this.isLoadingStats = false;
        }
      });

    this.isLoadingOrders = true;
    this.ordersError = '';
    this.ordersService.getOrders(1, 5)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: orders => {
          this.recentOrders = orders;
          this.isLoadingOrders = false;
        },
        error: () => {
          this.recentOrders = [];
          this.ordersError = 'Не удалось загрузить последние заказы';
          this.isLoadingOrders = false;
        }
      });
  }

  private setupStatusRows(statusDistribution: Array<{status: string, count: number}>): void {
    const total = statusDistribution.reduce((sum, item) => sum + Number(item.count || 0), 0);
    this.statusRows = statusDistribution.map(item => ({
      status: item.status,
      label: this.getStatusLabel(item.status),
      count: Number(item.count || 0),
      percent: total ? Math.round((Number(item.count || 0) / total) * 100) : 0,
      color: this.getStatusColor(item.status)
    }));

    this.updateChartData();
  }

  private updateChartData(): void {
    if (!this.statusRows.length) {
      this.chartData = null;
      return;
    }

    const panelBackground = this.getCssVariable('--panel-background', '#ffffff');
    this.chartData = {
      labels: this.statusRows.map(item => item.label),
      datasets: [{
        data: this.statusRows.map(item => item.count),
        backgroundColor: this.statusRows.map(item => item.color),
        borderWidth: 3,
        borderColor: panelBackground,
        hoverBorderColor: panelBackground
      }]
    };
  }

  private buildChartOptions(): ChartConfiguration<'doughnut'>['options'] {
    const textColor = this.getCssVariable('--color-text-secondary', '#64748b');
    const surfaceColor = this.getCssVariable('--panel-background', '#ffffff');
    const borderColor = this.getCssVariable('--color-border', '#d8e0ea');

    return {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '72%',
      layout: {
        padding: 4
      },
      plugins: {
        legend: {
          display: false
        },
        tooltip: {
          backgroundColor: surfaceColor,
          titleColor: textColor,
          bodyColor: textColor,
          borderColor,
          borderWidth: 1,
          padding: 12,
          displayColors: true
        }
      }
    };
  }

  private watchThemeChanges(): void {
    merge(
      this.themeService.currentTheme$,
      this.themeService.currentStyle$,
      this.themeService.currentSkin$
    )
      .pipe(takeUntil(this.destroy$))
      .subscribe(() => {
        this.chartOptions = this.buildChartOptions();
        this.updateChartData();
      });
  }

  private normalizeStats(stats: Partial<DashboardStats> | null): DashboardStats {
    return {
      total_orders: Number(stats?.total_orders || 0),
      total_revenue: Number(stats?.total_revenue || 0),
      avg_order_value: Number(stats?.avg_order_value || 0),
      recent_orders: Number(stats?.recent_orders || 0),
      recent_revenue: Number(stats?.recent_revenue || 0),
      status_distribution: stats?.status_distribution || []
    };
  }

  private getStatusCount(statuses: string[]): number {
    return this.statusRows
      .filter(item => statuses.includes(item.status))
      .reduce((sum, item) => sum + item.count, 0);
  }

  private getCssVariable(name: string, fallback: string): string {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;
  }
}
