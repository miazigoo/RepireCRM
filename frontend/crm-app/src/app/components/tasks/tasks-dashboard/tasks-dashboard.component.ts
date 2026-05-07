import { Component, OnInit, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTableModule, MatTableDataSource } from '@angular/material/table';
import { MatPaginatorModule, MatPaginator, MatPaginatorIntl } from '@angular/material/paginator';
import { MatSortModule, MatSort } from '@angular/material/sort';
import { MatTabsModule } from '@angular/material/tabs';
import { MatChipsModule } from '@angular/material/chips';
import { MatMenuModule } from '@angular/material/menu';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatBadgeModule } from '@angular/material/badge';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatDividerModule } from '@angular/material/divider';
import { MatSelectModule } from '@angular/material/select';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { FormBuilder, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { TasksService } from '../../../services/tasks.service';
import { RussianPaginatorIntl } from '../../../core/i18n/russian-paginator-intl';

interface Task {
  id: number;
  title: string;
  description: string;
  status: 'pending' | 'in_progress' | 'completed' | 'cancelled' | 'overdue';
  priority: 'low' | 'normal' | 'high' | 'urgent';
  assignment_type: 'individual' | 'shop' | 'all_shops' | 'role';
  assigned_to?: string;
  assigned_shop?: string;
  due_date?: string;
  created_by: string;
  created_at: string;
  progress_percent: number;
  category?: string;
}

interface TasksSummary {
  total_tasks: number;
  status_breakdown: Record<string, number>;
  overdue_tasks: number;
  due_today: number;
  priority_breakdown: Record<string, number>;
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
  styleUrl: './tasks-dashboard.component.css',
  providers: [{ provide: MatPaginatorIntl, useClass: RussianPaginatorIntl }]
})
export class TasksDashboardComponent implements OnInit {
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

  selectedTab = 0; // 0 - Все задачи, 1 - Мои задачи, 2 - Созданные мной

  constructor(
    private fb: FormBuilder,
    private tasksService: TasksService,
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
    this.loadTasksSummary();
    this.loadTasks();
    this.setupFilters();
  }

  ngAfterViewInit(): void {
    this.dataSource.paginator = this.paginator;
    this.dataSource.sort = this.sort;
  }

  private setupFilters(): void {
    this.filtersForm.valueChanges.subscribe(() => {
      this.loadTasks();
    });
  }

  private loadTasksSummary(): void {
    this.tasksService.getMyTasksSummary().subscribe({
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

    const filters = { ...this.filtersForm.value };

    // Устанавливаем фильтр в зависимости от выбранной вкладки
    switch (this.selectedTab) {
      case 1: // Мои задачи
        filters.assigned_to_me = true;
        break;
      case 2: // Созданные мной
        filters.created_by_me = true;
        break;
    }

    this.tasksService.getTasks(filters).subscribe({
      next: (tasks) => {
        this.dataSource.data = tasks;
        this.loading = false;
      },
      error: (error) => {
        this.showError(error, 'Не удалось загрузить задачи');
        this.loading = false;
      }
    });
  }

  onTabChanged(index: number): void {
    this.selectedTab = index;
    this.loadTasks();
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
    this.snackBar.open('Форма создания задач будет добавлена отдельным экраном', 'Закрыть', {
      duration: 3500
    });
  }

  editTask(task: Task): void {
    this.snackBar.open(`Редактирование: ${task.title}`, 'Закрыть', {
      duration: 3000
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
    this.snackBar.open(`Задача: ${task.title}`, 'Закрыть', {
      duration: 3000
    });
  }

  addComment(task: Task): void {
    this.snackBar.open(`Комментарии к задаче: ${task.title}`, 'Закрыть', {
      duration: 3000
    });
  }

  showTemplatesNotice(): void {
    this.snackBar.open('Шаблоны задач доступны в API, отдельный экран еще не подключен', 'Закрыть', {
      duration: 3500
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
}
