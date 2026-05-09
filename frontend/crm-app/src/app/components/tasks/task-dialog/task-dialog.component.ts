import { CommonModule } from '@angular/common';
import { Component, Inject } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { Shop, User } from '../../../core/models/models';
import { Task, TaskPayload } from '../../../services/tasks.service';

export interface TaskDialogData {
  task?: Partial<Task> | null;
  users: User[];
  shops: Shop[];
}

@Component({
  selector: 'app-task-dialog',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatButtonModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatSelectModule,
    MatSlideToggleModule,
  ],
  templateUrl: './task-dialog.component.html',
  styleUrl: './task-dialog.component.scss',
})
export class TaskDialogComponent {
  readonly statuses = [
    { value: 'pending', label: 'Ожидает' },
    { value: 'in_progress', label: 'В работе' },
    { value: 'completed', label: 'Выполнена' },
    { value: 'cancelled', label: 'Отменена' },
  ];

  readonly priorities = [
    { value: 'normal', label: 'Обычный' },
    { value: 'high', label: 'Высокий' },
    { value: 'urgent', label: 'Срочный' },
    { value: 'low', label: 'Низкий' },
  ];

  readonly kinds = [
    { value: 'regular', label: 'Обычная' },
    { value: 'urgent', label: 'Срочная' },
    { value: 'global', label: 'Глобальная' },
    { value: 'planned', label: 'Плановая' },
  ];

  readonly substatuses = [
    { value: 'new', label: 'Новая' },
    { value: 'accepted', label: 'Принята' },
    { value: 'waiting', label: 'Ожидает' },
    { value: 'blocked', label: 'Заблокирована' },
    { value: 'review', label: 'На проверке' },
    { value: 'done', label: 'Готово' },
  ];

  taskForm: FormGroup;

  constructor(
    private fb: FormBuilder,
    private dialogRef: MatDialogRef<TaskDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: TaskDialogData,
  ) {
    this.taskForm = this.fb.group({
      title: [this.data.task?.title || '', [Validators.required, Validators.maxLength(200)]],
      description: [this.data.task?.description || '', Validators.required],
      assignment_type: [this.data.task?.assignment_type || 'individual', Validators.required],
      assigned_to_id: [this.data.task?.assigned_to_id || null],
      assigned_shop_id: [this.data.task?.assigned_shop_id || null],
      priority: [this.data.task?.priority || 'normal', Validators.required],
      kind: [this.data.task?.kind || 'regular', Validators.required],
      substatus: [this.data.task?.substatus || 'new', Validators.required],
      status: [this.data.task?.status || 'pending', Validators.required],
      due_date: [this.toLocalDateTime(this.data.task?.due_date)],
      is_paid: [this.data.task?.is_paid || false],
      payment_amount: [this.data.task?.payment_amount || 0, [Validators.min(0)]],
      progress_percent: [
        this.data.task?.progress_percent || 0,
        [Validators.min(0), Validators.max(100)],
      ],
    });
  }

  submit(): void {
    if (this.taskForm.invalid) {
      this.taskForm.markAllAsTouched();
      return;
    }

    const value = this.taskForm.getRawValue();
    const payload: TaskPayload & Partial<Task> = {
      ...value,
      due_date: value.due_date ? new Date(value.due_date).toISOString() : null,
      assigned_to_id: value.assignment_type === 'individual' ? value.assigned_to_id : null,
      assigned_shop_id: value.assignment_type === 'shop' ? value.assigned_shop_id : null,
      payment_amount: Number(value.payment_amount || 0),
      progress_percent: Number(value.progress_percent || 0),
    } as TaskPayload & Partial<Task>;
    this.dialogRef.close(payload);
  }

  getUserName(user: User): string {
    return [user.last_name, user.first_name].filter(Boolean).join(' ') || user.username;
  }

  private toLocalDateTime(value?: string): string | null {
    if (!value) {
      return null;
    }
    const date = new Date(value);
    const offset = date.getTimezoneOffset() * 60000;
    return new Date(date.getTime() - offset).toISOString().slice(0, 16);
  }
}
