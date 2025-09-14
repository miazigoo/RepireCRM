import { Routes } from '@angular/router';

export const ORDERS_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () => import('./orders-list/orders-list.component').then(m => m.OrdersListComponent)
  },
  {
    path: 'new',
    loadComponent: () => import('./order-form/order-form.component').then(m => m.OrderFormComponent)
  },
  {
    path: ':id',
    loadComponent: () => import('./order-detail/order-detail.component').then(m => m.OrderDetailComponent)
  },
  {
    path: ':id/edit',
    loadComponent: () => import('./order-form/order-form.component').then(m => m.OrderFormComponent)
  }
];