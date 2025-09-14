// @Component({
//   selector: 'app-order-card',
//   template: `
//     <mat-card class="order-card">
//       <mat-card-header>
//         <mat-card-title>Заказ №{{ order.id }}</mat-card-title>
//         <mat-card-subtitle>{{ order.customer.lastName }} {{ order.customer.firstName }}</mat-card-subtitle>
//       </mat-card-header>
//       <mat-card-content>
//         <mat-chip-set>
//           <mat-chip [color]="getStatusColor(order.status)">{{ order.status }}</mat-chip>
//         </mat-chip-set>
//       </mat-card-content>
//     </mat-card>
//   `
// })