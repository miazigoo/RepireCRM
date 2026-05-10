import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';
import { catchError, map } from 'rxjs/operators';
import { ApiService } from './api.service';

export interface Task {
  id: number;
  title: string;
  description: string;
  status: 'pending' | 'in_progress' | 'completed' | 'cancelled' | 'overdue';
  priority: 'low' | 'normal' | 'high' | 'urgent';
  kind: 'regular' | 'urgent' | 'global' | 'planned';
  substatus: 'new' | 'accepted' | 'waiting' | 'blocked' | 'review' | 'done';
  assignment_type: 'individual' | 'shop' | 'all_shops' | 'role';
  assigned_to_id?: number;
  assigned_to_name?: string;
  assigned_to?: string;
  assigned_shop_id?: number;
  assigned_shop_name?: string;
  assigned_shop?: string;
  due_date?: string;
  created_by: string;
  created_at: string;
  progress_percent: number;
  category?: string;
  is_paid: boolean;
  payment_amount: number;
}

export interface TaskPayload {
  title: string;
  description: string;
  assignment_type: 'individual' | 'shop' | 'all_shops' | 'role';
  assigned_to_id?: number | null;
  assigned_shop_id?: number | null;
  priority?: 'low' | 'normal' | 'high' | 'urgent';
  kind?: 'regular' | 'urgent' | 'global' | 'planned';
  substatus?: 'new' | 'accepted' | 'waiting' | 'blocked' | 'review' | 'done';
  due_date?: string | null;
  is_paid?: boolean;
  payment_amount?: number;
}

export interface TasksSummary {
  total_tasks: number;
  status_breakdown: Record<string, number>;
  overdue_tasks: number;
  due_today: number;
  priority_breakdown: Record<string, number>;
  completed_this_month?: number;
  paid_tasks_amount?: number;
}

export interface TaskTemplate {
  id: number;
  name: string;
  category?: string | null;
  title_template: string;
  default_priority: Task['priority'];
  estimated_hours?: number | null;
}

type TaskListResponse = Task[] | { items: Task[]; count?: number };

@Injectable({
  providedIn: 'root'
})
export class TasksService {
  constructor(private apiService: ApiService) {}

  getMyTasksSummary(filters?: Record<string, unknown>): Observable<TasksSummary> {
    return this.apiService.get<TasksSummary>('/tasks/my-tasks-summary', filters).pipe(
      catchError(() => of({
        total_tasks: 0,
        status_breakdown: {},
        overdue_tasks: 0,
        due_today: 0,
        priority_breakdown: {}
      }))
    );
  }

  getTasks(filters: Record<string, unknown>): Observable<Task[]> {
    return this.apiService.get<TaskListResponse>('/tasks', filters).pipe(
      map((response) => Array.isArray(response) ? response : response.items ?? []),
      catchError(() => of([]))
    );
  }

  createTask(payload: TaskPayload): Observable<Task> {
    return this.apiService.post<Task>('/tasks/', payload);
  }

  updateTask(taskId: number, data: Partial<Task>): Observable<Task> {
    return this.apiService.put<Task>(`/tasks/${taskId}`, data);
  }

  getTaskStatistics(params?: Record<string, unknown>): Observable<any> {
    return this.apiService.get<any>('/tasks/statistics', params);
  }

  getTaskTemplates(): Observable<TaskTemplate[]> {
    return this.apiService.get<TaskTemplate[]>('/tasks/templates').pipe(
      catchError(() => of([]))
    );
  }
}
