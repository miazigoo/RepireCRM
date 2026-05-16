import { Component, OnInit, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { NavigationEnd, Router, RouterLink, RouterOutlet } from '@angular/router';
import { MatSidenavModule, MatSidenav } from '@angular/material/sidenav';
import { MatButtonModule } from '@angular/material/button';
import { MatMenuModule } from '@angular/material/menu';
import { MatDividerModule } from '@angular/material/divider';
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
import { OrdersService } from '../../../services/orders.service';
import { AuthService } from '../../../services/auth.service';

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
    MatMenuModule,
    MatDividerModule,
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

  availableShops: Shop[] = [];
  pendingOrdersCount = 0;
  notificationsCount = 0;
  currentRouteTitle = 'Панель управления';
  sidebarCollapsed = false;
  profileAvatarFailed = false;
  private profileAvatarUrl: string | null = null;

  navigationGroups: NavigationGroup[] = [
    {
      label: 'Работа',
      items: [
        { label: 'Панель', icon: 'dashboard', route: '/dashboard' },
        { label: 'Заказы', icon: 'assignment', route: '/orders', badge: 'pendingOrdersCount' },
        { label: 'Задачи', icon: 'task_alt', route: '/tasks' },
        { label: 'Клиенты', icon: 'people', route: '/customers' },
        { label: 'Склад', icon: 'inventory_2', route: '/inventory' },
        { label: 'Услуги', icon: 'home_repair_service', route: '/services' },
        { label: 'Акции', icon: 'sell', route: '/promotions' }
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
        { label: 'Подписка и поддержка', icon: 'support_agent', route: '/admin/service', directorOnly: true },
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
    '/inventory/purchase-requests': 'Заявки поставщикам',
    '/inventory/purchase-requests/new': 'Заявка поставщику',
    '/inventory/purchase-orders/new': 'Заявка поставщику',
    '/notifications': 'Уведомления',
    '/services': 'Услуги',
    '/promotions': 'Акции и промокоды',
    '/reports': 'Отчеты',
    '/finance': 'Финансы',
    '/tasks': 'Задачи',
    '/profile': 'Профиль',
    '/admin': 'Администрирование',
    '/admin/users': 'Пользователи',
    '/admin/users/new': 'Новый пользователь',
    '/admin/shops': 'Магазины',
    '/admin/roles': 'Роли и права',
    '/admin/settings': 'Настройки',
    '/admin/service': 'Подписка и поддержка',
    '/themes': 'Темы'
  };

  constructor(
    private breakpointObserver: BreakpointObserver,
    private store: Store<AppState>,
    private router: Router,
    private dialog: MatDialog,
    private notificationService: NotificationService,
    private ordersService: OrdersService,
    private authService: AuthService
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
    this.sidebarCollapsed = this.readSidebarCollapsed();
    this.updateRouteTitle(this.router.url);
    this.router.events
      .pipe(filter((event): event is NavigationEnd => event instanceof NavigationEnd))
      .subscribe(event => {
        this.updateRouteTitle(event.urlAfterRedirects);
      });

    this.currentUser$.subscribe(user => {
      this.syncProfileAvatarState(user);
      this.currentUser = user;
      this.availableShops = user?.available_shops || [];
      if (user && this.availableShops.length === 0) {
        this.loadAvailableShops();
      }
    });

    this.currentShop$.subscribe(shop => {
      this.currentShop = shop;
      this.loadPendingOrdersCount();
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

  toggleSidebar(): void {
    this.sidebarCollapsed = !this.sidebarCollapsed;
    localStorage.setItem('repaircrm.sidebarCollapsed', String(this.sidebarCollapsed));
  }

  getCurrentShopName(): string {
    return this.currentShop?.name || 'Рабочее пространство';
  }

  getShopMeta(shop: Shop): string {
    const parts = [shop.city, shop.code].filter(Boolean);
    return parts.length > 0 ? parts.join(' · ') : 'Филиал';
  }

  getShopCountLabel(count: number): string {
    const mod10 = count % 10;
    const mod100 = count % 100;

    if (mod10 === 1 && mod100 !== 11) {
      return 'точка';
    }

    if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) {
      return 'точки';
    }

    return 'точек';
  }

  getUserDisplayName(): string {
    const fullName = [
      this.currentUser?.first_name,
      this.currentUser?.last_name,
    ].filter(Boolean).join(' ');

    return fullName || this.currentUser?.username || 'Пользователь';
  }

  getUserInitials(): string {
    const initials = [
      this.currentUser?.first_name?.charAt(0),
      this.currentUser?.last_name?.charAt(0),
    ].filter(Boolean).join('');

    return initials || this.currentUser?.username?.charAt(0)?.toUpperCase() || 'U';
  }

  onProfileAvatarError(): void {
    this.profileAvatarFailed = true;
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
    this.authService.getAvailableShops().subscribe({
      next: shops => {
        this.availableShops = shops.filter(shop => shop.is_active);
      },
      error: () => {
        this.availableShops = this.currentShop ? [this.currentShop] : [];
      }
    });
  }

  private loadPendingOrdersCount(): void {
    this.ordersService.getOrdersPage(1, 1, { status: 'received' }).subscribe({
      next: response => {
        this.pendingOrdersCount = response.count;
      },
      error: () => {
        this.pendingOrdersCount = 0;
      }
    });
  }

  private updateRouteTitle(url: string): void {
    const cleanUrl = this.getCleanUrl(url);
    this.currentRouteTitle = this.routeTitles[cleanUrl] || 'Рабочее пространство';
  }

  private getCleanUrl(url: string): string {
    return url.split('?')[0].replace(/\/\d+(\/edit)?$/, '');
  }

  private readSidebarCollapsed(): boolean {
    return localStorage.getItem('repaircrm.sidebarCollapsed') === 'true';
  }

  private syncProfileAvatarState(user: User | null): void {
    const nextAvatar = user?.avatar || null;
    if (nextAvatar !== this.profileAvatarUrl) {
      this.profileAvatarUrl = nextAvatar;
      this.profileAvatarFailed = false;
    }
  }
}
