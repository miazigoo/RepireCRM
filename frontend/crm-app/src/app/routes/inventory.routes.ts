import { Routes } from '@angular/router';

export const INVENTORY_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () => import('../components/inventory/inventory-dashboard/inventory-dashboard.component').then(m => m.InventoryDashboardComponent)
  },
  {
    path: 'items/new',
    loadComponent: () => import('../components/inventory/inventory-item-form/inventory-item-form.component').then(m => m.InventoryItemFormComponent)
  },
  {
    path: 'purchase-requests',
    loadComponent: () => import('../components/inventory/purchase-requests/purchase-requests.component').then(m => m.PurchaseRequestsComponent)
  },
  {
    path: 'purchase-requests/new',
    loadComponent: () => import('../components/inventory/purchase-order-form/purchase-order-form.component').then(m => m.PurchaseOrderFormComponent)
  },
  {
    path: 'purchase-orders/new',
    redirectTo: 'purchase-requests/new',
    pathMatch: 'full'
  }
];
