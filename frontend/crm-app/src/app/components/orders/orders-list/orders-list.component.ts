import { Component, OnInit, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { MatTableModule, MatTableDataSource } from '@angular/material/table';
import { MatPaginatorModule, MatPaginator } from '@angular/material/paginator';
import { MatSortModule, MatSort } from '@angular/material/sort';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatCardModule } from '@angular/material/card';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatMenuModule } from '@angular/material/menu';
import { FormBuilder, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { debounceTime, distinctUntilChanged } from 'rxjs/operators';
import { OrdersService } from '../../../core/services/orders.service';
import { Order, OrderStatus, OrderPriority } from '../../../core/models/models';

@Component({
  selector: 'app-orders-list',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    ReactiveFormsModule,
    MatTableModule,
    MatPaginatorModule,
    MatSortModule,
    MatInputModule,
    MatSelectModule,
    MatButtonModule,
    MatIconModule,
    MatChipsModule,
    MatCardModule,
    MatProgressSpinnerModule,
    MatMenuModule
  ],
  template: `
    <div class="orders-container">
      <div class="header">
        <h1>Заказы</h1>
        <button mat-raised-button color="primary" routerLink="/orders/new">
          <mat-icon>add</mat-icon>
          Новый заказ
        </button>
      </div>

      
      <mat-card class="filters-card">
        <mat-card-content>
          <form [formGroup]="filtersForm" class="filters-form">
            <mat-form-field class="search-field">
              <mat-label>Поиск</mat-label>
              <input matInput 
                     formControlName="search" 
                     placeholder="Номер заказа, клиент, устройство...">
              <mat-icon matSuffix>search</mat-icon>
            </mat-form-field>

            <mat-form-field>
              <mat-label>Статус</mat-label>
              <mat-select formControlName="status">
                <mat-option value="">Все статусы</mat-option>
                <mat-option value="received">Принят</mat-option>
                <mat-option value="diagnosed">Диагностирован</mat-option>
                <mat-option value="waiting_parts">Ожидание запчастей</mat-option>
                <mat-option value="in_repair">В ремонте</mat-option>
                <mat-option value="testing">Тестирование</mat-option>
                <mat-option value="ready">Готов</mat-option>
                <mat-option value="completed">Выдан</mat-option>
                <mat-option value="cancelled">Отменен</mat-option>
              </mat-select>
            </mat-form-field>

            <mat-form-field>
              <mat-label>Приоритет</mat-label>
              <mat-select formControlName="priority">
                <mat-option value="">Все приоритеты</mat-option>
                <mat-option value="low">Низкий</mat-option>
                <mat-option value="normal">Обычный</mat-option>
                <mat-option value="high">Высокий</mat-option>
                <mat-option value="urgent">Срочный</mat-option>
              </mat-select>
            </mat-form-field>

            <button mat-button (click)="clearFilters()">
              <mat-icon>clear</mat-icon>
              Очистить
            </button>
          </form>
        </mat-card-content>
      </mat-card>

      
      <mat-card class="table-card">
        <mat-card-content>
          <div class="table-container">
            <table mat-table [dataSource]="dataSource" matSort class="orders-table">
              
              
              <ng-container matColumnDef="order_number">
                <th mat-header-cell *matHeaderCellDef mat-sort-header>Номер заказа</th>
                <td mat-cell *matCellDef="let order">
                  <a [routerLink]="['/orders', order.id]" class="order-link">
                    {{ order.order_number }}
                  </a>
                </td>
              </ng-container>

              
              <ng-container matColumnDef="customer">
                <th mat-header-cell *matHeaderCellDef>Клиент</th>
                <td mat-cell *matCellDef="let order">
                  <div class="customer-info">
                    <div class="customer-name">
                      {{ order.customer.last_name }} {{ order.customer.first_name }}
                    </div>
                    <div class="customer-phone">{{ order.customer.phone }}</div>
                  </div>
                </td>
              </ng-container>

              
              <ng-container matColumnDef="device">
                <th mat-header-cell *matHeaderCellDef>Устройство</th>
                <td mat-cell *matCellDef="let order">
                  <div class="device-info">
                    <div class="device-name">
                      {{ order.device.model.brand.name }} {{ order.device.model.name }}
                    </div>
                    <div class="device-details" *ngIf="order.device.color || order.device.storage_capacity">
                      {{ order.device.color }} {{ order.device.storage_capacity }}
                    </div>
                  </div>
                </td>
              </ng-container>

              
              <ng-container matColumnDef="status">
                <th mat-header-cell *matHeaderCellDef>Статус</th>
                <td mat-cell *matCellDef="let order">
                  <mat-chip [class]="'status-chip ' + order.status">
                    {{ getStatusLabel(order.status) }}
                  </mat-chip>
                </td>
              </ng-container>

              
              <ng-container matColumnDef="priority">
                <th mat-header-cell *matHeaderCellDef>Приоритет</th>
                <td mat-cell *matCellDef="let order">
                  <mat-chip [class]="'priority-chip ' + order.priority" 
                            *ngIf="order.priority !== 'normal'">
                    {{ getPriorityLabel(order.priority) }}
                  </mat-chip>
                </td>
              </ng-container>

              
              <ng-container matColumnDef="cost">
                <th mat-header-cell *matHeaderCellDef>Стоимость</th>
                <td mat-cell *matCellDef="let order">
                  <div class="cost-info">
                    <div class="final-cost" *ngIf="order.final_cost; else estimatedCost">
                      {{ order.final_cost | currency:'RUB':'symbol':'1.0-0' }}
                    </div>
                    <ng-template #estimatedCost>
                      <div class="estimated-cost">
                        ~{{ order.cost_estimate | currency:'RUB':'symbol':'1.0-0' }}
                      </div>
                    </ng-template>
                    <div class="remaining-payment" *ngIf="order.remaining_payment > 0">
                      Доплата: {{ order.remaining_payment | currency:'RUB':'symbol':'1.0-0' }}
                    </div>
                  </div>
                </td>
              </ng-container>

              
              <ng-container matColumnDef="created_at">
                <th mat-header-cell *matHeaderCellDef mat-sort-header>Дата создания</th>
                <td mat-cell *matCellDef="let order">
                  {{ order.created_at | date:'dd.MM.yyyy HH:mm' }}
                </td>
              </ng-container>

              
              <ng-container matColumnDef="actions">
                <th mat-header-cell *matHeaderCellDef>Действия</th>
                <td mat-cell *matCellDef="let order">
                  <button mat-icon-button [matMenuTriggerFor]="actionsMenu">
                    <mat-icon>more_vert</mat-icon>
                  </button>
                  <mat-menu #actionsMenu="matMenu">
                    <button mat-menu-item [routerLink]="['/orders', order.id]">
                      <mat-icon>visibility</mat-icon>
                      <span>Просмотр</span>
                    </button>
                    <button mat-menu-item [routerLink]="['/orders', order.id, 'edit']">
                      <mat-icon>edit</mat-icon>
                      <span>Редактировать</span>
                    </button>
                    <button mat-menu-item (click)="changeStatus(order)">
                      <mat-icon>swap_horiz</mat-icon>
                      <span>Изменить статус</span>
                    </button>
                  </mat-menu>
                </td>
              </ng-container>

              <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
              <tr mat-row *matRowDef="let row; columns: displayedColumns;"></tr>
            </table>

            <div class="loading-shade" *ngIf="loading">
              <mat-spinner></mat-spinner>
            </div>
          </div>

          <mat-paginator 
            [pageSizeOptions]="[10, 20, 50, 100]"
            [pageSize]="20"
            showFirstLastButtons>
          </mat-paginator>
        </mat-card-content>
      </mat-card>
    </div>
  `,
  styles: [`
    .orders-container {
      max-width: 1400px;
      margin: 0 auto;
    }

    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 24px;
    }

    .header h1 {
      margin: 0;
      color: #333;
    }

    .filters-card {
      margin-bottom: 24px;
    }

    .filters-form {
      display: grid;
      grid-template-columns: 2fr 1fr 1fr auto;
      gap: 16px;
      align-items: center;
    }

    .search-field {
      min-width: 300px;
    }

    .table-card {
      position: relative;
    }

    .table-container {
      position: relative;
      max-height: 600px;
      overflow: auto;
    }

    .orders-table {
      width: 100%;
    }

    .order-link {
      color: #1976d2;
      text-decoration: none;
      font-weight: 500;
    }

    .order-link:hover {
      text-decoration: underline;
    }

    .customer-info, .device-info {
      display: flex;
      flex-direction: column;
    }

    .customer-name, .device-name {
      font-weight: 500;
      margin-bottom: 2px;
    }

    .customer-phone, .device-details {
      font-size: 12px;
      color: #666;
    }

    .cost-info {
      display: flex;
      flex-direction: column;
    }

    .final-cost {
      font-weight: 500;
      color: #2e7d32;
    }

    .estimated-cost {
      color: #f57c00;
    }

    .remaining-payment {
      font-size: 12px;
      color: #d32f2f;
    }

    @media (max-width: 768px) {
      .filters-form {
        grid-template-columns: 1fr;
      }
      
      .search-field {
        min-width: auto;
      }
      
      .header {
        flex-direction: column;
        gap: 16px;
        align-items: stretch;
      }
    }
  `]
})
export class OrdersListComponent implements OnInit {
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;

  displayedColumns: string[] = [
    'order_number', 
    'customer', 
    'device', 
    'status', 
    'priority', 
    'cost', 
    'created_at', 
    'actions'
  ];

  dataSource = new MatTableDataSource<Order>();
  filtersForm: FormGroup;
  loading = false;

  constructor(
    private ordersService: OrdersService,
    private fb: FormBuilder
  ) {
    this.filtersForm = this.fb.group({
      search: [''],
      status: [''],
      priority: ['']
    });
  }

  ngOnInit(): void {
    this.loadOrders();
    this.setupFilters();
  }

  ngAfterViewInit(): void {
    this.dataSource.paginator = this.paginator;
    this.dataSource.sort = this.sort;
  }

  private loadOrders(): void {
    this.loading = true;
    const filters = this.filtersForm.value;
    
    this.ordersService.getOrders(1, 100, filters).subscribe({
      next: (orders) => {
        this.dataSource.data = orders;
        this.loading = false;
      },
      error: (error) => {
        console.error('Error loading orders:', error);
        this.loading = false;
      }
    });
  }

  private setupFilters(): void {
    this.filtersForm.valueChanges
      .pipe(
        debounceTime(300),
        distinctUntilChanged()
      )
      .subscribe(() => {
        this.loadOrders();
      });
  }

  clearFilters(): void {
    this.filtersForm.reset();
  }

  changeStatus(order: Order): void {
    // Откроем диалог для изменения статуса
    console.log('Change status for order:', order.id);
  }

  getStatusLabel(status: OrderStatus): string {
    const statusLabels: {[key in OrderStatus]: string} = {
      'received': 'Принят',
      'diagnosed': 'Диагностирован',
      'waiting_parts': 'Ожидание запчастей',
      'in_repair': 'В ремонте',
      'testing': 'Тестирование',
      'ready': 'Готов',
      'completed': 'Выдан',
      'cancelled': 'Отменен'
    };
    return statusLabels[status];
  }

  getPriorityLabel(priority: OrderPriority): string {
    const priorityLabels: {[key in OrderPriority]: string} = {
      'low': 'Низкий',
      'normal': 'Обычный',
      'high': 'Высокий',
      'urgent': 'Срочный'
    };
    return priorityLabels[priority];
  }
}