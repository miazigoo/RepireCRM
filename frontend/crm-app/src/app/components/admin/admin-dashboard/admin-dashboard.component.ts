// frontend/crm-app/src/app/components/admin/admin-dashboard/admin-dashboard.component.ts
import { Component, OnDestroy, OnInit } from '@angular/core';
import { NgIf, NgFor, DatePipe } from '@angular/common';
import { RouterModule } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { Subscription } from 'rxjs';
import { AdminService } from '../../../services/admin.service';
import { AuthService } from '../../../services/auth.service';
import { SubscriptionPlan, SubscriptionStatus, User } from '../../../core/models/models';

interface SystemStats {
  total_users: number;
  active_users: number;
  total_shops: number;
  active_shops: number;
  total_orders_today: number;
  total_revenue_today: number;
  system_health: 'good' | 'warning' | 'error';
}

@Component({
  selector: 'app-admin-dashboard',
  standalone: true,
  imports: [NgIf, NgFor, DatePipe, RouterModule, MatButtonModule, MatProgressSpinnerModule],
  templateUrl: './admin-dashboard.component.html',
  styleUrl: './admin-dashboard.component.scss',
})
export class AdminDashboardComponent implements OnInit, OnDestroy {
  stats: SystemStats | null = null;
  subscription: SubscriptionStatus | null = null;
  subscriptionPlans: SubscriptionPlan[] = [];
  loading = false;
  subscriptionLoading = false;
  statsScope: 'current' | 'all' = 'current';
  canViewGlobalStats = false;
  private userSubscription?: Subscription;

  quickActions = [
    {
      title: 'Управление пользователями',
      description: 'Добавление, редактирование и удаление пользователей',
      icon: 'people',
      route: '/admin/users',
      tone: 'users',
    },
    {
      title: 'Управление магазинами',
      description: 'Настройка филиалов и их параметров',
      icon: 'store',
      route: '/admin/shops',
      tone: 'shops',
    },
    {
      title: 'Роли и разрешения',
      description: 'Настройка ролей и прав доступа',
      icon: 'security',
      route: '/admin/roles',
      tone: 'roles',
    },
    {
      title: 'Системные настройки',
      description: 'Общие настройки системы',
      icon: 'settings',
      route: '/admin/settings',
      tone: 'settings',
    },
  ];

  constructor(
    private adminService: AdminService,
    private authService: AuthService,
  ) {}

  ngOnInit(): void {
    this.updateGlobalStatsPermission(this.authService.currentUser);
    this.userSubscription = this.authService.currentUser$.subscribe((user) => {
      this.updateGlobalStatsPermission(user);
    });
    this.loadSystemStats();
    this.loadSubscription();
  }

  ngOnDestroy(): void {
    this.userSubscription?.unsubscribe();
  }

  private loadSystemStats(): void {
    this.loading = true;
    this.adminService.getSystemStatistics(this.statsScope === 'all').subscribe({
      next: (stats) => {
        this.stats = stats;
        this.loading = false;
      },
      error: (error) => {
        console.error('Error loading system statistics:', error);
        this.loading = false;
      },
    });
  }

  setStatsScope(scope: 'current' | 'all'): void {
    if (scope === 'all' && !this.canViewGlobalStats) {
      return;
    }

    if (this.statsScope === scope) {
      return;
    }

    this.statsScope = scope;
    this.loadSystemStats();
  }

  getStatsScopeLabel(): string {
    return this.statsScope === 'all' ? 'Все филиалы' : 'Текущий филиал';
  }

  getHealthStatusColor(health: string): string {
    switch (health) {
      case 'good':
        return '#4caf50';
      case 'warning':
        return '#ff9800';
      case 'error':
        return '#f44336';
      default:
        return '#757575';
    }
  }

  getHealthStatusText(health: string): string {
    switch (health) {
      case 'good':
        return 'Отлично';
      case 'warning':
        return 'Предупреждение';
      case 'error':
        return 'Ошибка';
      default:
        return 'Неизвестно';
    }
  }

  getHealthStatusClass(health: string): string {
    switch (health) {
      case 'good':
        return 'good';
      case 'warning':
        return 'warning';
      case 'error':
        return 'error';
      default:
        return 'unknown';
    }
  }

  changeSubscription(planCode: string): void {
    this.subscriptionLoading = true;
    this.adminService.changeSubscription(planCode).subscribe({
      next: (subscription) => {
        this.subscription = subscription;
        this.subscriptionLoading = false;
      },
      error: () => (this.subscriptionLoading = false),
    });
  }

  getSubscriptionBackground(): string {
    return this.subscription?.color_hex || '#607d8b';
  }

  getSubscriptionGradient(): string {
    const color = this.getSubscriptionBackground();
    return `linear-gradient(90deg, ${color} ${this.subscription?.remaining_percent || 0}%, #e5e7eb 0)`;
  }

  formatCurrency(value: number | null | undefined): string {
    return `${new Intl.NumberFormat('ru-RU', {
      maximumFractionDigits: 0,
    }).format(value || 0)} ₽`;
  }

  formatNumber(value: number | null | undefined): string {
    return new Intl.NumberFormat('ru-RU').format(value || 0);
  }

  private loadSubscription(): void {
    this.subscriptionLoading = true;
    this.adminService.getSubscriptionStatus().subscribe({
      next: (subscription) => {
        this.subscription = subscription;
        this.loadSubscriptionPlans();
      },
      error: () => (this.subscriptionLoading = false),
    });
  }

  private loadSubscriptionPlans(): void {
    this.adminService.getSubscriptionPlans().subscribe({
      next: (plans) => {
        this.subscriptionPlans = plans.filter((plan) => plan.code !== 'trial');
        this.subscriptionLoading = false;
      },
      error: () => (this.subscriptionLoading = false),
    });
  }

  private updateGlobalStatsPermission(user: User | null): void {
    const permissionCodes = [
      ...(user?.role?.permission_codes || []),
      ...(user?.role?.permissions?.map((permission) => permission.codename) || []),
    ];

    this.canViewGlobalStats = Boolean(
      user?.is_director ||
      user?.role?.code === 'admin' ||
      permissionCodes.includes('reports.view_all_shops'),
    );

    if (!this.canViewGlobalStats && this.statsScope === 'all') {
      this.statsScope = 'current';
      this.loadSystemStats();
    }
  }
}
