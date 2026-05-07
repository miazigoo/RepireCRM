import { Component, OnInit, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { NavigationEnd, Router, RouterLink, RouterOutlet } from '@angular/router';
import { MatSidenavModule, MatSidenav } from '@angular/material/sidenav';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { MatBadgeModule } from '@angular/material/badge';
import { MatDividerModule } from '@angular/material/divider';
import { MatSelectModule } from '@angular/material/select';
import { MatListModule } from '@angular/material/list';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import { Store } from '@ngrx/store';
import { Observable } from 'rxjs';
import { filter, map, shareReplay } from 'rxjs/operators';
import { AppState } from '../../../store/app.state';
import { selectCurrentUser, selectCurrentShop } from '../../../store/auth/auth.selectors';
import * as AuthActions from '../../../store/auth/auth.actions';
import { User, Shop } from '../../../core/models/models';
import { HelpGuideDialogComponent } from '../../help/help-guide-dialog/help-guide-dialog.component';
import { NotificationService } from '../../../services/notification.service';

interface NavigationItem {
  label: string;
  icon: string;
  route?: string;
  badge?: 'pendingOrdersCount' | 'notificationsCount';
  action?: 'help';
  directorOnly?: boolean;
  activeRoutes?: string[];
}

interface NavigationGroup {
  label: string;
  items: NavigationItem[];
}

@Component({
  selector: 'app-main-layout',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    RouterOutlet,
    MatSidenavModule,
    MatButtonModule,
    MatIconModule,
    MatMenuModule,
    MatBadgeModule,
    MatDividerModule,
    MatSelectModule,
    MatListModule,
    MatTooltipModule,
    MatDialogModule,
  ],
  templateUrl: './main-layout.component.html',
  styleUrl: './main-layout.component.scss'
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
  currentRouteTitle = 'Панель управления';

  navigationGroups: NavigationGroup[] = [
    {
      label: 'Работа',
      items: [
        { label: 'Панель', icon: 'dashboard', route: '/dashboard' },
        { label: 'Заказы', icon: 'assignment', route: '/orders', badge: 'pendingOrdersCount' },
        { label: 'Клиенты', icon: 'people', route: '/customers' },
        { label: 'Склад', icon: 'inventory_2', route: '/inventory' }
      ]
    },
    {
      label: 'Контроль',
      items: [
        { label: 'Уведомления', icon: 'notifications', route: '/notifications', badge: 'notificationsCount' },
        { label: 'Отчеты', icon: 'query_stats', route: '/reports' },
        { label: 'Справочник', icon: 'help_center', action: 'help' }
      ]
    },
    {
      label: 'Система',
      items: [
        {
          label: 'Администрирование',
          icon: 'admin_panel_settings',
          route: '/admin',
          directorOnly: true,
          activeRoutes: ['/admin/users', '/admin/shops', '/admin/roles']
        },
        { label: 'Настройки', icon: 'tune', route: '/admin/settings', directorOnly: true },
        { label: 'Темы', icon: 'palette', route: '/themes' }
      ]
    }
  ];

  private routeTitles: Record<string, string> = {
    '/dashboard': 'Панель управления',
    '/orders': 'Заказы',
    '/orders/new': 'Новый заказ',
    '/customers': 'Клиенты',
    '/inventory': 'Склад',
    '/inventory/items/new': 'Новый товар',
    '/inventory/purchase-orders/new': 'Заказ поставщику',
    '/notifications': 'Уведомления',
    '/reports': 'Отчеты',
    '/admin': 'Администрирование',
    '/admin/users': 'Пользователи',
    '/admin/users/new': 'Новый пользователь',
    '/admin/shops': 'Магазины',
    '/admin/roles': 'Роли и права',
    '/admin/settings': 'Настройки',
    '/themes': 'Темы'
  };

  constructor(
    private breakpointObserver: BreakpointObserver,
    private store: Store<AppState>,
    private router: Router,
    private dialog: MatDialog,
    private notificationService: NotificationService
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
    this.updateRouteTitle(this.router.url);
    this.router.events
      .pipe(filter((event): event is NavigationEnd => event instanceof NavigationEnd))
      .subscribe(event => {
        this.updateRouteTitle(event.urlAfterRedirects);
      });

    this.currentUser$.subscribe(user => {
      this.currentUser = user;
      if (user?.is_director) {
        this.loadAvailableShops();
      }
    });

    this.currentShop$.subscribe(shop => {
      this.currentShop = shop;
    });

    this.notificationService.unreadCount$.subscribe(count => {
      this.notificationsCount = count;
    });
    this.notificationService.refresh();
    this.loadPendingOrdersCount();
  }

  switchShop(shopId: number): void {
    this.store.dispatch(AuthActions.switchShop({ shopId }));
  }

  logout(): void {
    this.store.dispatch(AuthActions.logout());
  }

  openHelp(): void {
    this.dialog.open(HelpGuideDialogComponent, {
      width: 'min(980px, calc(100vw - 32px))',
      maxWidth: '980px',
      maxHeight: 'calc(100vh - 32px)',
      panelClass: 'guide-dialog-panel',
      autoFocus: false
    });
  }

  isNavItemVisible(item: NavigationItem): boolean {
    return !item.directorOnly || this.currentUser?.is_director === true;
  }

  isNavigationItemActive(item: NavigationItem): boolean {
    if (!item.route) {
      return false;
    }

    const cleanUrl = this.getCleanUrl(this.router.url);

    if (item.activeRoutes) {
      return cleanUrl === item.route || item.activeRoutes.some(route => cleanUrl === route || cleanUrl.startsWith(`${route}/`));
    }

    return cleanUrl === item.route || cleanUrl.startsWith(`${item.route}/`);
  }

  getBadgeValue(item: NavigationItem): number {
    if (item.badge === 'pendingOrdersCount') {
      return this.pendingOrdersCount;
    }

    if (item.badge === 'notificationsCount') {
      return this.notificationsCount;
    }

    return 0;
  }

  onNavigationAction(item: NavigationItem): void {
    if (item.action === 'help') {
      this.openHelp();
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

  private loadPendingOrdersCount(): void {
    // Загрузка количества ожидающих заказов
    this.pendingOrdersCount = 5;
  }

  private updateRouteTitle(url: string): void {
    const cleanUrl = this.getCleanUrl(url);
    this.currentRouteTitle = this.routeTitles[cleanUrl] || 'Рабочее пространство';
  }

  private getCleanUrl(url: string): string {
    return url.split('?')[0].replace(/\/\d+(\/edit)?$/, '');
  }
}
