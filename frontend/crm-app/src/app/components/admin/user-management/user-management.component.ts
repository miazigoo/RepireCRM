// import { Component } from '@angular/core';
// import { User } from '../../../core/models/models';
// import { Role } from '../../../core/models/models';
// import { UserService } from '../../core/services/user.service';

// @Component({
//     selector: 'app-user-management',
//     template: `
//       <mat-table [dataSource]="users">
//         <ng-container matColumnDef="name">
//           <mat-header-cell *matHeaderCellDef>Имя</mat-header-cell>
//           <mat-cell *matCellDef="let user">{{ user.firstName }} {{ user.lastName }}</mat-cell>
//         </ng-container>
//         <ng-container matColumnDef="role">
//           <mat-header-cell *matHeaderCellDef>Роль</mat-header-cell>
//           <mat-cell *matCellDef="let user">
//             <mat-select [(value)]="user.role" (selectionChange)="updateUserRole(user)">
//               <mat-option *ngFor="let role of roles" [value]="role">{{ role.name }}</mat-option>
//             </mat-select>
//           </mat-cell>
//         </ng-container>
//       </mat-table>
//     `
//   })
//   export class UserManagementComponent {
    // users: User[] = [];
    // roles: Role[] = [];
  
    // constructor(private userService: UserService) {
    //   this.userService.getUsers().subscribe((users) => {
    //     this.users = users;
    //   });
    // }
  // }