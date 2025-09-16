import { Routes } from '@angular/router';

export const ORDERS_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () => import('../components/orders/orders-list/orders-list.component').then(m => m.OrdersListComponent)
  },
  {
    path: 'new',
    loadComponent: () => import('../components/orders/order-form/order-form.component').then(m => m.OrderFormComponent)
  },
  {
    path: ':id',
    loadComponent: () => import('../components/orders/order-detail/order-detail.component').then(m => m.OrderDetailComponent)
  },
  {
    path: ':id/edit',
    loadComponent: () => import('../components/orders/order-form/order-form.component').then(m => m.OrderFormComponent)
  }
];