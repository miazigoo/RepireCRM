import { CommonModule } from '@angular/common';
import { Component, Inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';

export type AvatarPreviewAction = 'edit' | 'replace';

export interface AvatarPreviewDialogData {
  avatarUrl: string;
  displayName: string;
}

@Component({
  selector: 'app-avatar-preview-dialog',
  standalone: true,
  imports: [CommonModule, MatButtonModule, MatDialogModule],
  templateUrl: './avatar-preview-dialog.component.html',
  styleUrl: './avatar-preview-dialog.component.scss',
})
export class AvatarPreviewDialogComponent {
  constructor(
    private dialogRef: MatDialogRef<AvatarPreviewDialogComponent, AvatarPreviewAction | null>,
    @Inject(MAT_DIALOG_DATA) public data: AvatarPreviewDialogData,
  ) {}

  close(action: AvatarPreviewAction | null = null): void {
    this.dialogRef.close(action);
  }
}
