import { Routes } from '@angular/router';
import { AuthGuard } from './core/guards/auth.guard';

export const routes: Routes = [
  {
    path: 'login',
    loadComponent: () => import('./components/auth/login/login.component').then(m => m.LoginComponent)
  },
  {
    path: '',
    canActivate: [AuthGuard],
    loadComponent: () => import('./components/layout/main-layout/main-layout.component').then(m => m.MainLayoutComponent),
    children: [
      {
        path: 'dashboard',
        loadComponent: () => import('./components/dashboard/dashboard.component').then(m => m.DashboardComponent)
      },
      {
        path: 'orders',
        loadChildren: () => import('./routes/orders.routes').then(m => m.ORDERS_ROUTES)
      },
      {
        path: 'customers',
        loadChildren: () => import('./routes/customers.routes').then(m => m.CUSTOMERS_ROUTES)
      },
      {
        path: 'inventory',
        loadChildren: () => import('./routes/inventory.routes').then(m => m.INVENTORY_ROUTES)
      },
      {
        path: 'reports',
        loadComponent: () => import('./components/reports/reports-dashboard/reports-dashboard.component').then(m => m.ReportsDashboardComponent)
      },
      {
        path: 'services',
        loadComponent: () => import('./components/services/services-management/services-management.component').then(m => m.ServicesManagementComponent)
      },
      {
        path: 'promotions',
        loadComponent: () => import('./components/promotions/promotions-management/promotions-management.component').then(m => m.PromotionsManagementComponent)
      },
      {
        path: 'notifications',
        loadComponent: () => import('./components/layout/notifications/notifications.component').then(m => m.NotificationsComponent)
      },
      {
        path: 'finance',
        loadComponent: () => import('./components/finance/finance-dashboard/finance-dashboard.component').then(m => m.FinanceDashboardComponent)
      },
      {
        path: 'tasks',
        loadComponent: () => import('./components/tasks/tasks-dashboard/tasks-dashboard.component').then(m => m.TasksDashboardComponent)
      },
      {
        path: 'tasks/:taskId',
        loadComponent: () => import('./components/tasks/tasks-dashboard/tasks-dashboard.component').then(m => m.TasksDashboardComponent)
      },
      {
        path: 'themes',
        loadComponent: () => import('./components/themes/themes-page/themes-page.component').then(m => m.ThemesPageComponent)
      },
      {
        path: 'profile',
        loadComponent: () => import('./components/profile/profile.component').then(m => m.ProfileComponent)
      },
      {
        path: 'admin',
        loadChildren: () => import('./routes/admin.routes').then(m => m.ADMIN_ROUTES)
      },
      {
        path: '',
        redirectTo: 'dashboard',
        pathMatch: 'full'
      }
    ]
  },
  {
    path: '**',
    redirectTo: ''
  }
];
