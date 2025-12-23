import { Component, OnInit, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTableModule, MatTableDataSource } from '@angular/material/table';
import { MatPaginatorModule, MatPaginator } from '@angular/material/paginator';
import { MatSortModule, MatSort } from '@angular/material/sort';
import { MatTabsModule } from '@angular/material/tabs';
import { MatChipsModule } from '@angular/material/chips';
import { MatMenuModule } from '@angular/material/menu';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatBadgeModule } from '@angular/material/badge';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { MatSelectModule } from '@angular/material/select';
import { MatFormFieldModule } from '@angular/material/form-field';
import { FormBuilder, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { TasksService } from '../../../services/tasks.service';

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
    MatDialogModule,
    MatSelectModule,
    MatFormFieldModule
  ],
  templateUrl: './tasks-dashboard.component.html',
  styleUrl: './tasks-dashboard.component.css'
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
    private dialog: MatDialog
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
        console.error('Error loading tasks summary:', error);
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
        console.error('Error loading tasks:', error);
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
    // Открыть диалог создания задачи или перейти на форму
  }

  editTask(task: Task): void {
    // Открыть диалог редактирования задачи
  }

  changeTaskStatus(task: Task, newStatus: string): void {
    this.tasksService.updateTask(task.id, { status: newStatus }).subscribe({
      next: () => {
        task.status = newStatus as any;
        if (newStatus === 'completed') {
          task.progress_percent = 100;
        }
      },
      error: (error) => {
        console.error('Error updating task status:', error);
      }
    });
  }

  updateProgress(task: Task, progress: number): void {
    this.tasksService.updateTask(task.id, { progress_percent: progress }).subscribe({
      next: () => {
        task.progress_percent = progress;
      },
      error: (error) => {
        console.error('Error updating task progress:', error);
      }
    });
  }

  viewTask(task: Task): void {
    // Переход к детальному просмотру задачи
  }

  addComment(task: Task): void {
    // Открыть диалог добавления комментария
  }

  getObjectKeys(obj: any): string[] {
    return Object.keys(obj);
  }
}
