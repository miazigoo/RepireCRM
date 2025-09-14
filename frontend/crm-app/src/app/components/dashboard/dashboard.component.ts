import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatGridListModule } from '@angular/material/grid-list';
import { MatTableModule } from '@angular/material/table';
import { MatChipsModule } from '@angular/material/chips';
import { Router } from '@angular/router';
import { Observable } from 'rxjs';
import { OrdersService } from '../../services/orders.service';
import { Order } from '../../core/models/models';
import { BaseChartDirective } from 'ng2-charts';
import { ChartConfiguration, ChartData, ChartType } from 'chart.js';

interface DashboardStats {
  total_orders: number;
  total_revenue: number;
  avg_order_value: number;
  recent_orders: number;
  recent_revenue: number;
  status_distribution: Array<{status: string, count: number}>;
}

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatIconModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatGridListModule,
    MatTableModule,
    MatChipsModule,
    BaseChartDirective
  ],
  template: `
    <div class="dashboard-container">
      <h1>Панель управления</h1>

      
      <div class="stats-grid">
        <mat-card class="stat-card orders-card">
          <mat-card-content>
            <div class="stat-content">
              <div class="stat-icon">
                <mat-icon>assignment</mat-icon>
              </div>
              <div class="stat-info">
                <h3>{{ stats?.recent_orders || 0 }}</h3>
                <p>Заказов за месяц</p>
                <span class="stat-change positive">
                  +{{ ((stats?.recent_orders || 0) / (stats?.total_orders || 1) * 100).toFixed(1) }}%
                </span>
              </div>
            </div>
          </mat-card-content>
        </mat-card>

        <mat-card class="stat-card revenue-card">
          <mat-card-content>
            <div class="stat-content">
              <div class="stat-icon">
                <mat-icon>attach_money</mat-icon>
              </div>
              <div class="stat-info">
                <h3>{{ (stats?.recent_revenue || 0) | currency:'RUB':'symbol':'1.0-0' }}</h3>
                <p>Выручка за месяц</p>
                <span class="stat-change positive">+15.3%</span>
              </div>
            </div>
          </mat-card-content>
        </mat-card>

        <mat-card class="stat-card avg-card">
          <mat-card-content>
            <div class="stat-content">
              <div class="stat-icon">
                <mat-icon>trending_up</mat-icon>
              </div>
              <div class="stat-info">
                <h3>{{ (stats?.avg_order_value || 0) | currency:'RUB':'symbol':'1.0-0' }}</h3>
                <p>Средний чек</p>
                <span class="stat-change positive">+8.2%</span>
              </div>
            </div>
          </mat-card-content>
        </mat-card>

        <mat-card class="stat-card total-card">
          <mat-card-content>
            <div class="stat-content">
              <div class="stat-icon">
                <mat-icon>analytics</mat-icon>
              </div>
              <div class="stat-info">
                <h3>{{ stats?.total_orders || 0 }}</h3>
                <p>Всего заказов</p>
                <span class="stat-change neutral">Общая статистика</span>
              </div>
            </div>
          </mat-card-content>
        </mat-card>
      </div>

      
      <div class="content-row">
        
        <mat-card class="chart-card">
          <mat-card-header>
            <mat-card-title>Распределение по статусам</mat-card-title>
          </mat-card-header>
          <mat-card-content>
            <div class="chart-container" *ngIf="chartData">
              <canvas baseChart
                      [data]="chartData"
                      [type]="chartType"
                      [options]="chartOptions">
              </canvas>
            </div>
            <div class="loading-container" *ngIf="!chartData">
              <mat-spinner></mat-spinner>
            </div>
          </mat-card-content>
        </mat-card>

        
        <mat-card class="recent-orders-card">
          <mat-card-header>
            <mat-card-title>Последние заказы</mat-card-title>
            <button mat-button color="primary" routerLink="/orders">
              Все заказы
            </button>
          </mat-card-header>
          <mat-card-content>
            <div class="orders-list" *ngIf="recentOrders.length > 0; else noOrders">
              <div class="order-item" *ngFor="let order of recentOrders">
                <div class="order-info">
                  <div class="order-header">
                    <span class="order-number">{{ order.order_number }}</span>
                    <mat-chip [class]="'status-chip ' + order.status">
                      {{ getStatusLabel(order.status) }}
                    </mat-chip>
                  </div>
                  <div class="order-details">
                    <span class="customer-name">
                      {{ order.customer.last_name }} {{ order.customer.first_name }}
                    </span>
                    <span class="device-info">
                      {{ order.device.model.brand.name }} {{ order.device.model.name }}
                    </span>
                  </div>
                  <div class="order-meta">
                    <span class="order-cost">
                      {{ (order.final_cost || order.cost_estimate) | currency:'RUB':'symbol':'1.0-0' }}
                    </span>
                    <span class="order-date">
                      {{ order.created_at | date:'dd.MM.yyyy HH:mm' }}
                    </span>
                  </div>
                </div>
                <button mat-icon-button 
                        color="primary"
                        [routerLink]="['/orders', order.id]">
                  <mat-icon>arrow_forward</mat-icon>
                </button>
              </div>
            </div>
            <ng-template #noOrders>
              <div class="no-data">
                <mat-icon>assignment</mat-icon>
                <p>Нет заказов</p>
              </div>
            </ng-template>
          </mat-card-content>
        </mat-card>
      </div>

      
      <mat-card class="quick-actions-card">
        <mat-card-header>
          <mat-card-title>Быстрые действия</mat-card-title>
        </mat-card-header>
        <mat-card-content>
          <div class="actions-grid">
            <button mat-raised-button color="primary" routerLink="/orders/new">
              <mat-icon>add</mat-icon>
              Новый заказ
            </button>
            <button mat-raised-button color="accent" routerLink="/customers/new">
              <mat-icon>person_add</mat-icon>
              Новый клиент
            </button>
            <button mat-raised-button routerLink="/orders" [queryParams]="{status: 'ready'}">
              <mat-icon>check_circle</mat-icon>
              Готовые заказы
            </button>
            <button mat-raised-button routerLink="/reports">
              <mat-icon>assessment</mat-icon>
              Отчеты
            </button>
          </div>
        </mat-card-content>
      </mat-card>
    </div>
  `,
  styles: [`
    .dashboard-container {
      max-width: 1200px;
      margin: 0 auto;
    }

    h1 {
      color: #333;
      margin-bottom: 24px;
    }

    .stats-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
      gap: 20px;
      margin-bottom: 24px;
    }

    .stat-card {
      height: 120px;
    }

    .stat-content {
      display: flex;
      align-items: center;
      height: 100%;
    }

    .stat-icon {
      margin-right: 16px;
    }

    .stat-icon mat-icon {
      font-size: 48px;
      height: 48px;
      width: 48px;
      opacity: 0.7;
    }

    .orders-card .stat-icon mat-icon { color: #2196f3; }
    .revenue-card .stat-icon mat-icon { color: #4caf50; }
    .avg-card .stat-icon mat-icon { color: #ff9800; }
    .total-card .stat-icon mat-icon { color: #9c27b0; }

    .stat-info h3 {
      margin: 0 0 4px 0;
      font-size: 24px;
      font-weight: 500;
    }

    .stat-info p {
      margin: 0 0 4px 0;
      color: #666;
      font-size: 14px;
    }

    .stat-change {
      font-size: 12px;
      padding: 2px 6px;
      border-radius: 12px;
    }

    .stat-change.positive {
      background: #e8f5e8;
      color: #2e7d32;
    }

    .stat-change.neutral {
      background: #f5f5f5;
      color: #666;
    }

    .content-row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 20px;
      margin-bottom: 24px;
    }

    .chart-card, .recent-orders-card {
      height: 400px;
    }

    .chart-container {
      height: 300px;
      position: relative;
    }

    .loading-container {
      display: flex;
      justify-content: center;
      align-items: center;
      height: 300px;
    }

    .orders-list {
      max-height: 320px;
      overflow-y: auto;
    }

    .order-item {
      display: flex;
      align-items: center;
      padding: 12px 0;
      border-bottom: 1px solid #eee;
    }

    .order-item:last-child {
      border-bottom: none;
    }

    .order-info {
      flex: 1;
    }

    .order-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 4px;
    }

    .order-number {
      font-weight: 500;
      color: #1976d2;
    }

    .order-details {
      display: flex;
      flex-direction: column;
      gap: 2px;
      margin-bottom: 4px;
    }

    .customer-name {
      font-weight: 500;
      font-size: 14px;
    }

    .device-info {
      color: #666;
      font-size: 12px;
    }

    .order-meta {
      display: flex;
      justify-content: space-between;
      font-size: 12px;
      color: #888;
    }

    .order-cost {
      font-weight: 500;
      color: #4caf50;
    }

    .quick-actions-card {
      margin-bottom: 24px;
    }

    .actions-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 16px;
    }

    .actions-grid button {
      height: 56px;
      font-size: 16px;
    }

    .actions-grid button mat-icon {
      margin-right: 8px;
    }

    .no-data {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 200px;
      color: #999;
    }

    .no-data mat-icon {
      font-size: 48px;
      height: 48px;
      width: 48px;
      margin-bottom: 16px;
    }

    @media (max-width: 768px) {
      .content-row {
        grid-template-columns: 1fr;
      }
      
      .stats-grid {
        grid-template-columns: 1fr;
      }
      
      .actions-grid {
        grid-template-columns: 1fr;
      }
    }
  `]
})
export class DashboardComponent implements OnInit {
  stats: DashboardStats | null = null;
  recentOrders: Order[] = [];
  
  // Chart configuration
  chartType: ChartType = 'doughnut';
  chartData: ChartData<'doughnut'> | null = null;
  chartOptions: ChartConfiguration['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'bottom'
      }
    }
  };

  constructor(
    private ordersService: OrdersService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.loadDashboardData();
  }

  private loadDashboardData(): void {
    // Загружаем статистику
    this.ordersService.getStatistics().subscribe(stats => {
      this.stats = stats;
      this.setupChart(stats.status_distribution);
    });

    // Загружаем последние заказы
    this.ordersService.getOrders(1, 5).subscribe(orders => {
      this.recentOrders = orders;
    });
  }

  private setupChart(statusDistribution: Array<{status: string, count: number}>): void {
    const statusLabels = statusDistribution.map(item => this.getStatusLabel(item.status));
    const statusData = statusDistribution.map(item => item.count);
    const statusColors = statusDistribution.map(item => this.getStatusColor(item.status));

    this.chartData = {
      labels: statusLabels,
      datasets: [{
        data: statusData,
        backgroundColor: statusColors,
        borderWidth: 2,
        borderColor: '#fff'
      }]
    };
  }

  getStatusLabel(status: string): string {
    const statusLabels: {[key: string]: string} = {
      'received': 'Принят',
      'diagnosed': 'Диагностирован',
      'waiting_parts': 'Ожидание запчастей',
      'in_repair': 'В ремонте',
      'testing': 'Тестирование',
      'ready': 'Готов',
      'completed': 'Выдан',
      'cancelled': 'Отменен'
    };
    return statusLabels[status] || status;
  }

  private getStatusColor(status: string): string {
    const statusColors: {[key: string]: string} = {
      'received': '#2196f3',
      'diagnosed': '#ff9800',
      'waiting_parts': '#9c27b0',
      'in_repair': '#ffc107',
      'testing': '#00bcd4',
      'ready': '#4caf50',
      'completed': '#8bc34a',
      'cancelled': '#f44336'
    };
    return statusColors[status] || '#757575';
  }
}