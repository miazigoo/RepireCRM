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
