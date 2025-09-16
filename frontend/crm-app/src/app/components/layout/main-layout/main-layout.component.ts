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
import { NotificationsComponent } from '../notifications/notifications.component';

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
    MatListModule,
    NotificationsComponent
  ],
  templateUrl: './main-layout.component.html',
  styleUrl: './main-layout.component.css'
})
export class MainLayoutComponent implements OnInit {
  @ViewChild('drawer') drawer!: MatSidenav;

  isHandset$: Observable<boolean>;

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
    this.isHandset$ = this.breakpointObserver.observe(Breakpoints.Handset)
      .pipe(
        map(result => result.matches),
        shareReplay()
      );
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
