import { Routes } from '@angular/router';
import { AuthGuard } from './core/guards/auth.guard';

export const routes: Routes = [
  {
    path: 'login',
    loadComponent: () => import('./components/auth/login/login.component').then(m => m.LoginComponent)
  },
  {
    path: 'portal',
    loadComponent: () => import('./components/client-portal/client-portal.component').then(m => m.ClientPortalComponent)
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
        path: 'finance',
        loadComponent: () => import('./components/finance/finance-dashboard/finance-dashboard.component').then(m => m.FinanceDashboardComponent)
      },
      {
        path: 'tasks',
        loadComponent: () => import('./components/tasks/tasks-dashboard/tasks-dashboard.component').then(m => m.TasksDashboardComponent)
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
