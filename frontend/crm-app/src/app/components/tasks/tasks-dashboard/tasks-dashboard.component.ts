import { Component, OnDestroy, OnInit, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTableModule, MatTableDataSource } from '@angular/material/table';
import { MatPaginatorModule, MatPaginator, MatPaginatorIntl } from '@angular/material/paginator';
import { MatSortModule, MatSort } from '@angular/material/sort';
import { MatTabsModule } from '@angular/material/tabs';
import { MatChipsModule } from '@angular/material/chips';
import { MatMenuModule } from '@angular/material/menu';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatBadgeModule } from '@angular/material/badge';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatDividerModule } from '@angular/material/divider';
import { MatSelectModule } from '@angular/material/select';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { FormBuilder, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { combineLatest, Subscription } from 'rxjs';
import { TasksService, Task, TaskPayload, TaskTemplate } from '../../../services/tasks.service';
import { RussianPaginatorIntl } from '../../../core/i18n/russian-paginator-intl';
import { AdminService } from '../../../services/admin.service';
import { AuthService } from '../../../services/auth.service';
import { Shop, User } from '../../../core/models/models';
import { TaskDialogComponent } from '../task-dialog/task-dialog.component';

interface TasksSummary {
  total_tasks: number;
  status_breakdown: Record<string, number>;
  overdue_tasks: number;
  due_today: number;
  priority_breakdown: Record<string, number>;
  completed_this_month?: number;
  paid_tasks_amount?: number;
}

@Component({
  selector: 'app-tasks-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    ReactiveFormsModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatTableModule,
    MatPaginatorModule,
    MatSortModule,
    MatTabsModule,
    MatChipsModule,
    MatMenuModule,
    MatDialogModule,
    MatProgressBarModule,
    MatBadgeModule,
    MatTooltipModule,
    MatDividerModule,
    MatSelectModule,
    MatFormFieldModule,
    MatInputModule,
    MatSnackBarModule
  ],
  templateUrl: './tasks-dashboard.component.html',
  styleUrl: './tasks-dashboard.component.scss',
  providers: [{ provide: MatPaginatorIntl, useClass: RussianPaginatorIntl }]
})
export class TasksDashboardComponent implements OnInit, OnDestroy {
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;

  filtersForm: FormGroup;
  loading = false;

  displayedColumns = ['title', 'status', 'priority', 'assigned_to', 'progress', 'due_date', 'actions'];
  dataSource = new MatTableDataSource<Task>();

  tasksSummary: TasksSummary = {
    total_tasks: 0,
    status_breakdown: {},
    overdue_tasks: 0,
    due_today: 0,
    priority_breakdown: {}
  };
  users: User[] = [];
  shops: Shop[] = [];
  templates: TaskTemplate[] = [];

  selectedTab = 0; // 0 - Все задачи, 1 - Мои задачи, 2 - Созданные мной
  private canViewAllTasks = false;
  private userSubscription?: Subscription;
  private routeSubscription?: Subscription;
  private pendingRouteTaskId: number | null = null;
  private openedRouteTaskId: number | null = null;

  constructor(
    private fb: FormBuilder,
    private tasksService: TasksService,
    private adminService: AdminService,
    private authService: AuthService,
    private route: ActivatedRoute,
    private dialog: MatDialog,
    private snackBar: MatSnackBar
  ) {
    this.filtersForm = this.fb.group({
      status: [''],
      priority: [''],
      assigned_to_me: [false],
      search: ['']
    });
  }

  ngOnInit(): void {
    this.canViewAllTasks = this.userCanViewAllTasks(this.authService.currentUser);
    this.userSubscription = this.authService.currentUser$.subscribe(user => {
      const nextCanViewAll = this.userCanViewAllTasks(user);
      if (nextCanViewAll !== this.canViewAllTasks) {
        this.canViewAllTasks = nextCanViewAll;
        this.loadTasksSummary();
        this.loadTasks();
      }
    });
    this.loadTasksSummary();
    this.loadTasks();
    this.loadAssignees();
    this.loadTemplates();
    this.setupFilters();
    this.watchRouteTask();
  }

  ngAfterViewInit(): void {
    this.dataSource.paginator = this.paginator;
    this.dataSource.sort = this.sort;
  }

  ngOnDestroy(): void {
    this.userSubscription?.unsubscribe();
    this.routeSubscription?.unsubscribe();
  }

  private setupFilters(): void {
    this.filtersForm.valueChanges.subscribe(() => {
      this.loadTasksSummary();
      this.loadTasks();
    });
  }

  private loadTasksSummary(): void {
    this.tasksService.getMyTasksSummary(this.buildTaskFilters()).subscribe({
      next: (summary) => {
        this.tasksSummary = summary;
      },
      error: (error) => {
        this.showError(error, 'Не удалось загрузить сводку задач');
      }
    });
  }

  private loadTasks(): void {
    this.loading = true;

    const filters = this.buildTaskFilters();

    this.tasksService.getTasks(filters).subscribe({
      next: (tasks) => {
        this.dataSource.data = tasks;
        this.loading = false;
        this.openRouteTaskIfNeeded();
      },
      error: (error) => {
        this.showError(error, 'Не удалось загрузить задачи');
        this.loading = false;
      }
    });
  }

  onTabChanged(index: number): void {
    this.selectedTab = index;
    this.loadTasksSummary();
    this.loadTasks();
  }

  private buildTaskFilters(): Record<string, unknown> {
    const filters: Record<string, unknown> = { ...this.filtersForm.value };
    delete filters['assigned_to_me'];
    delete filters['created_by_me'];

    if (this.canViewAllTasks && this.selectedTab !== 1) {
      filters['all_shops'] = true;
    }

    if (this.selectedTab === 1) {
      filters['assigned_to_me'] = true;
    } else if (this.selectedTab === 2) {
      filters['created_by_me'] = true;
    }

    return filters;
  }

  private userCanViewAllTasks(user: User | null): boolean {
    return Boolean(
      user?.is_director ||
      user?.role?.permission_codes?.includes('tasks.view_all_tasks')
    );
  }

  getStatusClass(status: string): string {
    switch (status) {
      case 'pending': return 'status-pending';
      case 'in_progress': return 'status-in-progress';
      case 'completed': return 'status-completed';
      case 'cancelled': return 'status-cancelled';
      case 'overdue': return 'status-overdue';
      default: return '';
    }
  }

  getStatusLabel(status: string): string {
    switch (status) {
      case 'pending': return 'Ожидает';
      case 'in_progress': return 'В работе';
      case 'completed': return 'Выполнена';
      case 'cancelled': return 'Отменена';
      case 'overdue': return 'Просрочена';
      default: return status;
    }
  }

  getPriorityClass(priority: string): string {
    switch (priority) {
      case 'low': return 'priority-low';
      case 'normal': return 'priority-normal';
      case 'high': return 'priority-high';
      case 'urgent': return 'priority-urgent';
      default: return '';
    }
  }

  getPriorityLabel(priority: string): string {
    switch (priority) {
      case 'low': return 'Низкий';
      case 'normal': return 'Обычный';
      case 'high': return 'Высокий';
      case 'urgent': return 'Срочный';
      default: return priority;
    }
  }

  getPriorityIcon(priority: string): string {
    switch (priority) {
      case 'low': return 'keyboard_arrow_down';
      case 'normal': return 'remove';
      case 'high': return 'keyboard_arrow_up';
      case 'urgent': return 'priority_high';
      default: return 'remove';
    }
  }

  getKindLabel(kind: string): string {
    switch (kind) {
      case 'urgent': return 'Срочная';
      case 'global': return 'Глобальная';
      case 'planned': return 'Плановая';
      case 'regular': return 'Обычная';
      default: return kind;
    }
  }

  getSubstatusLabel(substatus: string): string {
    switch (substatus) {
      case 'new': return 'Новая';
      case 'accepted': return 'Принята';
      case 'waiting': return 'Ожидает';
      case 'blocked': return 'Заблокирована';
      case 'review': return 'На проверке';
      case 'done': return 'Готово';
      default: return substatus;
    }
  }

  formatMoney(value: number | undefined): string {
    return `${new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 0 }).format(value || 0)} ₽`;
  }

  getProgressColor(progress: number): string {
    if (progress >= 80) return 'primary';
    if (progress >= 50) return 'accent';
    if (progress >= 20) return 'warn';
    return 'warn';
  }

  isDueSoon(dueDate?: string): boolean {
    if (!dueDate) return false;
    const due = new Date(dueDate);
    const now = new Date();
    const diffHours = (due.getTime() - now.getTime()) / (1000 * 60 * 60);
    return diffHours <= 24 && diffHours > 0;
  }

  isOverdue(dueDate?: string): boolean {
    if (!dueDate) return false;
    const due = new Date(dueDate);
    const now = new Date();
    return due.getTime() < now.getTime();
  }

  createTask(): void {
    this.openTaskDialog();
  }

  createTaskFromTemplate(template: TaskTemplate): void {
    const title = this.cleanTemplateText(template.title_template) || template.name;
    const draft: Partial<Task> = {
      title,
      description: title,
      priority: template.default_priority || 'normal',
      kind: 'planned',
      substatus: 'new',
      status: 'pending',
      assignment_type: 'individual',
      is_paid: false,
      payment_amount: 0,
      progress_percent: 0,
      category: template.category || undefined,
    };

    this.openTaskDialog(draft);
  }

  private openTaskDialog(task?: Partial<Task>): void {
    const dialogRef = this.dialog.open(TaskDialogComponent, {
      width: 'min(880px, calc(100vw - 28px))',
      maxWidth: '880px',
      maxHeight: 'calc(100vh - 32px)',
      panelClass: 'task-dialog-panel',
      autoFocus: false,
      data: {
        task,
        users: this.users,
        shops: this.shops,
      },
    });

    dialogRef.afterClosed().subscribe((payload?: TaskPayload) => {
      if (!payload) {
        return;
      }
      this.tasksService.createTask(payload).subscribe({
        next: () => {
          this.loadTasks();
          this.loadTasksSummary();
          this.snackBar.open('Задача создана', 'Закрыть', { duration: 2500 });
        },
        error: (error) => this.showError(error, 'Не удалось создать задачу'),
      });
    });
  }

  editTask(task: Task): void {
    const dialogRef = this.dialog.open(TaskDialogComponent, {
      width: 'min(880px, calc(100vw - 28px))',
      maxWidth: '880px',
      maxHeight: 'calc(100vh - 32px)',
      panelClass: 'task-dialog-panel',
      autoFocus: false,
      data: {
        task,
        users: this.users,
        shops: this.shops,
      },
    });

    dialogRef.afterClosed().subscribe((payload?: Partial<Task>) => {
      if (!payload) {
        return;
      }
      this.tasksService.updateTask(task.id, payload).subscribe({
        next: () => {
          this.loadTasks();
          this.loadTasksSummary();
          this.snackBar.open('Задача обновлена', 'Закрыть', { duration: 2500 });
        },
        error: (error) => this.showError(error, 'Не удалось обновить задачу'),
      });
    });
  }

  changeTaskStatus(task: Task, newStatus: string): void {
    this.tasksService.updateTask(task.id, { status: newStatus as Task['status'] }).subscribe({
      next: () => {
        task.status = newStatus as Task['status'];
        if (newStatus === 'completed') {
          task.progress_percent = 100;
        }
        this.loadTasksSummary();
        this.snackBar.open('Статус задачи обновлен', 'Закрыть', {
          duration: 2500
        });
      },
      error: (error) => {
        this.showError(error, 'Не удалось обновить статус задачи');
      }
    });
  }

  updateProgress(task: Task, progress: number): void {
    this.tasksService.updateTask(task.id, { progress_percent: progress }).subscribe({
      next: () => {
        task.progress_percent = progress;
        this.snackBar.open('Прогресс задачи обновлен', 'Закрыть', {
          duration: 2500
        });
      },
      error: (error) => {
        this.showError(error, 'Не удалось обновить прогресс задачи');
      }
    });
  }

  viewTask(task: Task): void {
    this.editTask(task);
  }

  addComment(task: Task): void {
    this.snackBar.open(`Комментарии к задаче: ${task.title}`, 'Закрыть', {
      duration: 3000
    });
  }

  getObjectKeys(obj: any): string[] {
    return Object.keys(obj);
  }

  private showError(error: any, fallback: string): void {
    const message = error?.error?.detail || error?.error?.error || fallback;
    this.snackBar.open(message, 'Закрыть', {
      duration: 4000
    });
  }

  private loadAssignees(): void {
    this.adminService.getUsers(1, 100).subscribe({
      next: (users) => {
        this.users = users;
      },
      error: () => {
        this.users = [];
      }
    });
    this.authService.getAvailableShops().subscribe({
      next: (shops) => {
        this.shops = shops;
      },
      error: () => {
        this.shops = [];
      }
    });
  }

  private loadTemplates(): void {
    this.tasksService.getTaskTemplates().subscribe({
      next: templates => {
        this.templates = templates;
      },
      error: () => {
        this.templates = [];
      },
    });
  }

  private cleanTemplateText(value: string): string {
    return value.replace(/\{[^}]+\}/g, '').replace(/\s+/g, ' ').trim();
  }

  private watchRouteTask(): void {
    this.routeSubscription = combineLatest([
      this.route.paramMap,
      this.route.queryParamMap,
    ]).subscribe(([params, query]) => {
      const rawTaskId = params.get('taskId') || query.get('task_id') || query.get('taskId');
      const taskId = rawTaskId ? Number(rawTaskId) : NaN;

      this.pendingRouteTaskId = Number.isInteger(taskId) && taskId > 0 ? taskId : null;
      if (this.pendingRouteTaskId !== this.openedRouteTaskId) {
        this.openedRouteTaskId = null;
      }
      this.openRouteTaskIfNeeded();
    });
  }

  private openRouteTaskIfNeeded(): void {
    if (!this.pendingRouteTaskId || this.openedRouteTaskId === this.pendingRouteTaskId || this.loading) {
      return;
    }

    const task = this.dataSource.data.find(item => item.id === this.pendingRouteTaskId);
    if (!task) {
      return;
    }

    this.openedRouteTaskId = task.id;
    this.viewTask(task);
  }
}
