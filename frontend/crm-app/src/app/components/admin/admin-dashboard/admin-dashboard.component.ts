// frontend/crm-app/src/app/components/admin/admin-dashboard/admin-dashboard.component.ts
import { Component, OnInit } from '@angular/core';
import { NgIf, NgFor, CurrencyPipe } from '@angular/common';
import { RouterModule } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatGridListModule } from '@angular/material/grid-list';
import { AdminService } from '../../../services/admin.service';

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
  imports: [
    NgIf, NgFor, CurrencyPipe, RouterModule,
    MatCardModule, MatButtonModule, MatIconModule,
    MatProgressSpinnerModule, MatGridListModule
  ],
  templateUrl: './admin-dashboard.component.html',
  styleUrl: './admin-dashboard.component.css'
})
export class AdminDashboardComponent implements OnInit {
  stats: SystemStats | null = null;
  loading = false;

  quickActions = [
    {
      title: 'Управление пользователями',
      description: 'Добавление, редактирование и удаление пользователей',
      icon: 'people',
      route: '/admin/users',
      color: 'primary'
    },
    {
      title: 'Управление магазинами',
      description: 'Настройка филиалов и их параметров',
      icon: 'store',
      route: '/admin/shops',
      color: 'accent'
    },
    {
      title: 'Роли и разрешения',
      description: 'Настройка ролей и прав доступа',
      icon: 'security',
      route: '/admin/roles',
      color: 'warn'
    },
    {
      title: 'Системные настройки',
      description: 'Общие настройки системы',
      icon: 'settings',
      route: '/admin/settings',
      color: 'primary'
    }
  ];

  constructor(private adminService: AdminService) {}

  ngOnInit(): void {
    this.loadSystemStats();
  }

  private loadSystemStats(): void {
    this.loading = true;
    this.adminService.getSystemStatistics().subscribe({
      next: (stats) => {
        this.stats = stats;
        this.loading = false;
      },
      error: (error) => {
        console.error('Error loading system statistics:', error);
        this.loading = false;
      }
    });
  }

  getHealthStatusColor(health: string): string {
    switch (health) {
      case 'good': return '#4caf50';
      case 'warning': return '#ff9800';
      case 'error': return '#f44336';
      default: return '#757575';
    }
  }

  getHealthStatusText(health: string): string {
    switch (health) {
      case 'good': return 'Отлично';
      case 'warning': return 'Предупреждение';
      case 'error': return 'Ошибка';
      default: return 'Неизвестно';
    }
  }
}
