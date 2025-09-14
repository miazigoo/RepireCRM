import { Component, OnInit, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet, Router } from '@angular/router';
import { MatSidenavModule, MatSidenav } from '@angular/material/sidenav';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { MatBadgeModule } from '@angular/material/badge';
import { MatSelectModule } from '@angular/material/select';
import { MatListModule } from '@angular/material/list';
import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import { Store } from '@ngrx/store';
import { Observable } from 'rxjs';
import { map, shareReplay } from 'rxjs/operators';
import { AppState } from '../../../store/app.state';
import { selectCurrentUser, selectCurrentShop } from '../../../store/auth/auth.selectors';
import * as AuthActions from '../../../store/auth/auth.actions';
import { User, Shop } from '../../../core/models/models';

@Component({
  selector: 'app-main-layout',
  standalone: true,
  imports: [
    CommonModule,
    RouterOutlet,
    MatSidenavModule,
    MatToolbarModule,
    MatButtonModule,
    MatIconModule,
    MatMenuModule,
    MatBadgeModule,
    MatSelectModule,
    MatListModule
  ],
  template: `
    <mat-sidenav-container class="sidenav-container">
      <mat-sidenav #drawer 
                   class="sidenav" 
                   fixedInViewport
                   [attr.role]="(isHandset$ | async) ? 'dialog' : 'navigation'"
                   [mode]="(isHandset$ | async) ? 'over' : 'side'"
                   [opened]="(isHandset$ | async) === false">
        
        <div class="sidenav-header">
          <mat-icon class="app-icon">build</mat-icon>
          <h3>Repair CRM</h3>
        </div>

        
        <div class="shop-selector" *ngIf="currentUser?.is_director">
          <mat-select 
            [value]="currentShop?.id"
            (selectionChange)="switchShop($event.value)"
            placeholder="Выберите магазин">
            <mat-option *ngFor="let shop of availableShops" [value]="shop.id">
              {{ shop.name }}
            </mat-option>
          </mat-select>
        </div>

        <mat-nav-list>
          <a mat-list-item routerLink="/dashboard" routerLinkActive="active">
            <mat-icon matListItemIcon>dashboard</mat-icon>
            <span matListItemTitle>Панель управления</span>
          </a>
          
          <a mat-list-item routerLink="/orders" routerLinkActive="active">
            <mat-icon matListItemIcon>assignment</mat-icon>
            <span matListItemTitle>Заказы</span>
            <span matListItemMeta class="pending-orders-badge" 
                  *ngIf="pendingOrdersCount > 0">
              {{ pendingOrdersCount }}
            </span>
          </a>
          
          <a mat-list-item routerLink="/customers" routerLinkActive="active">
            <mat-icon matListItemIcon>people</mat-icon>
            <span matListItemTitle>Клиенты</span>
          </a>
          
          <a mat-list-item routerLink="/inventory" routerLinkActive="active">
            <mat-icon matListItemIcon>inventory</mat-icon>
            <span matListItemTitle>Склад</span>
          </a>
          
          <a mat-list-item routerLink="/reports" routerLinkActive="active">
            <mat-icon matListItemIcon>assessment</mat-icon>
            <span matListItemTitle>Отчеты</span>
          </a>
          
          <mat-divider></mat-divider>
          
          <a mat-list-item routerLink="/admin" routerLinkActive="active" 
             *ngIf="currentUser?.is_director">
            <mat-icon matListItemIcon>admin_panel_settings</mat-icon>
            <span matListItemTitle>Администрирование</span>
          </a>
          
          <a mat-list-item routerLink="/settings" routerLinkActive="active">
            <mat-icon matListItemIcon>settings</mat-icon>
            <span matListItemTitle>Настройки</span>
          </a>
        </mat-nav-list>
      </mat-sidenav>

      <mat-sidenav-content>
        <mat-toolbar class="repair-toolbar">
          <button type="button"
                  aria-label="Toggle sidenav"
                  mat-icon-button
                  (click)="drawer.toggle()"
                  *ngIf="isHandset$ | async">
            <mat-icon aria-label="Side nav toggle icon">menu</mat-icon>
          </button>
          
          <span class="current-shop-name" *ngIf="currentShop">
            {{ currentShop.name }}
          </span>
          
          <span class="spacer"></span>
          
          
          <button mat-icon-button [matMenuTriggerFor]="notificationsMenu">
            <mat-icon [matBadge]="notificationsCount" 
                      matBadgeColor="warn"
                      [matBadgeHidden]="notificationsCount === 0">
              notifications
            </mat-icon>
          </button>
          
          
          <button mat-icon-button [matMenuTriggerFor]="userMenu">
            <mat-icon>account_circle</mat-icon>
          </button>
        </mat-toolbar>

        
        <mat-menu #notificationsMenu="matMenu">
          <div class="notifications-header">
            <h4>Уведомления</h4>
          </div>
          <mat-divider></mat-divider>
          <div class="notifications-list" *ngIf="notifications.length > 0; else noNotifications">
            <button mat-menu-item *ngFor="let notification of notifications" 
                    (click)="handleNotification(notification)">
              <mat-icon [color]="notification.type === 'urgent' ? 'warn' : 'primary'">
                {{ getNotificationIcon(notification.type) }}
              </mat-icon>
              <span>{{ notification.message }}</span>
            </button>
          </div>
          <ng-template #noNotifications>
            <div class="no-notifications">
              <p>Нет новых уведомлений</p>
            </div>
          </ng-template>
        </mat-menu>

        
        <mat-menu #userMenu="matMenu">
          <div class="user-info">
            <p><strong>{{ currentUser?.first_name }} {{ currentUser?.last_name }}</strong></p>
            <p class="user-role">{{ currentUser?.role?.name }}</p>
          </div>
          <mat-divider></mat-divider>
          <button mat-menu-item routerLink="/profile">
            <mat-icon>person</mat-icon>
            <span>Профиль</span>
          </button>
          <button mat-menu-item (click)="logout()">
            <mat-icon>logout</mat-icon>
            <span>Выйти</span>
          </button>
        </mat-menu>

        
        <div class="content-container">
          <router-outlet></router-outlet>
        </div>
      </mat-sidenav-content>
    </mat-sidenav-container>
  `,
  styles: [`
    .sidenav-container {
      height: 100%;
    }

    .sidenav {
      width: 280px;
      background: #fafafa;
    }

    .sidenav-header {
      padding: 20px;
      background: linear-gradient(45deg, #1976d2, #42a5f5);
      color: white;
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .app-icon {
      font-size: 32px;
      height: 32px;
      width: 32px;
    }

    .sidenav-header h3 {
      margin: 0;
      font-weight: 300;
    }

    .shop-selector {
      padding: 16px;
      border-bottom: 1px solid #e0e0e0;
    }

    .shop-selector mat-select {
      width: 100%;
    }

    .sidenav .mat-mdc-list-item.active {
      background-color: #e3f2fd;
      color: #1976d2;
    }

    .pending-orders-badge {
      background: #f44336;
      color: white;
      border-radius: 12px;
      padding: 4px 8px;
      font-size: 12px;
      min-width: 20px;
      text-align: center;
    }

    .current-shop-name {
      font-weight: 500;
      margin-left: 16px;
    }

    .content-container {
      padding: 20px;
      min-height: calc(100vh - 64px);
      background: #f5f5f5;
    }

    .notifications-header {
      padding: 16px;
    }

    .notifications-header h4 {
      margin: 0;
      color: #666;
    }

    .notifications-list {
      max-height: 300px;
      overflow-y: auto;
    }

    .no-notifications {
      padding: 16px;
      text-align: center;
      color: #999;
    }

    .user-info {
      padding: 16px;
      border-bottom: 1px solid #e0e0e0;
    }

    .user-info p {
      margin: 4px 0;
    }

    .user-role {
      color: #666;
      font-size: 14px;
    }

    @media (max-width: 768px) {
      .content-container {
        padding: 16px;
      }
      
      .current-shop-name {
        display: none;
      }
    }
  `]
})
export class MainLayoutComponent implements OnInit {
  @ViewChild('drawer') drawer!: MatSidenav;

  isHandset$: Observable<boolean> = this.breakpointObserver.observe(Breakpoints.Handset)
    .pipe(
      map(result => result.matches),
      shareReplay()
    );

  currentUser$: Observable<User | null>;
  currentShop$: Observable<Shop | null>;
  currentUser: User | null = null;
  currentShop: Shop | null = null;
  
  availableShops: Shop[] = []; // Будет загружаться из API
  pendingOrdersCount = 0;
  notificationsCount = 0;
  notifications: any[] = [];

  constructor(
    private breakpointObserver: BreakpointObserver,
    private store: Store<AppState>,
    private router: Router
  ) {
    this.currentUser$ = this.store.select(selectCurrentUser);
    this.currentShop$ = this.store.select(selectCurrentShop);
  }

  ngOnInit(): void {
    this.currentUser$.subscribe(user => {
      this.currentUser = user;
      if (user?.is_director) {
        this.loadAvailableShops();
      }
    });

    this.currentShop$.subscribe(shop => {
      this.currentShop = shop;
    });

    this.loadNotifications();
    this.loadPendingOrdersCount();
  }

  switchShop(shopId: number): void {
    this.store.dispatch(AuthActions.switchShop({ shopId }));
  }

  logout(): void {
    this.store.dispatch(AuthActions.logout());
  }

  handleNotification(notification: any): void {
    // Обработка уведомления - переход к соответствующему разделу
    switch (notification.type) {
      case 'order_ready':
        this.router.navigate(['/orders', notification.orderId]);
        break;
      case 'low_stock':
        this.router.navigate(['/inventory']);
        break;
      default:
        break;
    }
  }

  getNotificationIcon(type: string): string {
    switch (type) {
      case 'order_ready': return 'check_circle';
      case 'urgent': return 'priority_high';
      case 'low_stock': return 'inventory';
      default: return 'info';
    }
  }

  private loadAvailableShops(): void {
    // Здесь будет загрузка доступных магазинов через сервис
    // Временно заглушка
    this.availableShops = [
      { id: 1, name: 'Ремонт+ Москва Центр', code: 'MSK01', is_active: true, timezone: 'Europe/Moscow', currency: 'RUB' },
      { id: 2, name: 'Ремонт+ СПб Невский', code: 'SPB01', is_active: true, timezone: 'Europe/Moscow', currency: 'RUB' }
    ];
  }

  private loadNotifications(): void {
    // Загрузка уведомлений через WebSocket или HTTP
    this.notifications = [
      {
        id: 1,
        type: 'order_ready',
        message: 'Заказ #MSK-000001 готов к выдаче',
        orderId: 1
      },
      {
        id: 2,
        type: 'urgent',
        message: 'Срочный заказ просрочен на 2 дня',
        orderId: 2
      }
    ];
    this.notificationsCount = this.notifications.length;
  }

  private loadPendingOrdersCount(): void {
    // Загрузка количества ожидающих заказов
    this.pendingOrdersCount = 5;
  }
}