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
import { RouterModule } from '@angular/router';

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
    RouterModule,
    MatCardModule,
    MatIconModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatGridListModule,
    MatTableModule,
    MatChipsModule,
    BaseChartDirective
  ],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.css'
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
