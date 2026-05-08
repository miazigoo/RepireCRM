import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { of } from 'rxjs';
import { Permission, Role } from '../../../core/models/models';
import { AdminService } from '../../../services/admin.service';
import { RoleManagementComponent } from './role-management.component';

describe('RoleManagementComponent', () => {
  let fixture: ComponentFixture<RoleManagementComponent>;
  let component: RoleManagementComponent;
  let adminService: jasmine.SpyObj<AdminService>;

  const permissions: Permission[] = [
    {
      id: 1,
      name: 'Назначать филиалы сотрудникам',
      code: 'users.manage_shop_access',
      category: 'users',
      category_label: 'Пользователи и доступ',
      description: 'Привязывать магазины к аккаунтам сотрудников.',
    },
    {
      id: 2,
      name: 'Создавать платежи',
      code: 'finance.add_payment',
      category: 'finance',
      category_label: 'Финансы',
      description: 'Принимать оплату по заказам и продажам.',
    },
    {
      id: 3,
      name: 'Просматривать заказы',
      code: 'orders.view_order',
      category: 'orders',
      category_label: 'Заказы',
    },
  ];

  beforeEach(async () => {
    adminService = jasmine.createSpyObj<AdminService>('AdminService', [
      'getRoles',
      'getPermissions',
      'getRole',
      'createRole',
      'updateRole',
      'deleteRole',
    ]);
    adminService.getRoles.and.returnValue(of([]));
    adminService.getPermissions.and.returnValue(of(permissions));
    adminService.getRole.and.returnValue(
      of({
        id: 10,
        name: 'Администратор филиала',
        code: 'shop_admin',
        permissions: [permissions[0], permissions[1]],
      } as Role),
    );

    await TestBed.configureTestingModule({
      imports: [RoleManagementComponent],
      providers: [provideNoopAnimations(), { provide: AdminService, useValue: adminService }],
    }).compileComponents();

    fixture = TestBed.createComponent(RoleManagementComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('groups permissions by Russian business categories', () => {
    expect(component.getObjectKeys(component.permissionsByCategory)).toEqual([
      'orders',
      'finance',
      'users',
    ]);
    expect(component.getCategoryLabel('finance')).toBe('Финансы');
    expect(component.getCategoryDescription('users')).toContain('Сотрудники');
  });

  it('selects role permissions for checkbox editing', () => {
    const role = {
      id: 10,
      name: 'Администратор филиала',
      code: 'shop_admin',
    } as Role;

    component.editRole(role);

    expect(adminService.getRole).toHaveBeenCalledOnceWith(10);
    expect(component.isPermissionSelected(permissions[0])).toBeTrue();
    expect(component.isPermissionSelected(permissions[1])).toBeTrue();
    expect(component.isPermissionSelected(permissions[2])).toBeFalse();
  });
});
