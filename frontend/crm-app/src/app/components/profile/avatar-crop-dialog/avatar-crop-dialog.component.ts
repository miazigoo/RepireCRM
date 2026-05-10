import { CommonModule } from '@angular/common';
import { AfterViewInit, Component, ElementRef, Inject, OnDestroy, ViewChild } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';

export interface AvatarCropDialogData {
  sourceUrl: string;
  fileName: string;
}

@Component({
  selector: 'app-avatar-crop-dialog',
  standalone: true,
  imports: [CommonModule, MatButtonModule, MatDialogModule],
  templateUrl: './avatar-crop-dialog.component.html',
  styleUrl: './avatar-crop-dialog.component.scss',
})
export class AvatarCropDialogComponent implements AfterViewInit, OnDestroy {
  @ViewChild('cropFrame') cropFrame?: ElementRef<HTMLDivElement>;
  @ViewChild('cropImage') cropImage?: ElementRef<HTMLImageElement>;

  readonly minZoom = 1;
  readonly maxZoom = 3;
  readonly outputSize = 512;

  frameSize = 360;
  zoom = 1;
  imageLoaded = false;
  imageLoadFailed = false;
  offsetX = 0;
  offsetY = 0;

  private naturalWidth = 0;
  private naturalHeight = 0;
  private dragging = false;
  private lastPointerX = 0;
  private lastPointerY = 0;
  private resizeObserver?: ResizeObserver;

  constructor(
    private dialogRef: MatDialogRef<AvatarCropDialogComponent, File | null>,
    @Inject(MAT_DIALOG_DATA) public data: AvatarCropDialogData,
  ) {}

  ngAfterViewInit(): void {
    this.updateFrameSize();
    if (typeof ResizeObserver !== 'undefined' && this.cropFrame?.nativeElement) {
      this.resizeObserver = new ResizeObserver(() => {
        this.updateFrameSize();
        this.constrainOffset();
      });
      this.resizeObserver.observe(this.cropFrame.nativeElement);
    }
  }

  ngOnDestroy(): void {
    this.resizeObserver?.disconnect();
  }

  get imageStyle(): Record<string, string> {
    const width = this.displayWidth;
    const height = this.displayHeight;
    const x = this.frameSize / 2 - width / 2 + this.offsetX;
    const y = this.frameSize / 2 - height / 2 + this.offsetY;

    return {
      width: `${width}px`,
      height: `${height}px`,
      transform: `translate(${x}px, ${y}px)`,
    };
  }

  onImageLoad(event: Event): void {
    const image = event.target as HTMLImageElement;
    this.naturalWidth = image.naturalWidth;
    this.naturalHeight = image.naturalHeight;
    this.imageLoaded = Boolean(this.naturalWidth && this.naturalHeight);
    this.imageLoadFailed = !this.imageLoaded;
    this.resetCrop();
  }

  onImageError(): void {
    this.imageLoaded = false;
    this.imageLoadFailed = true;
  }

  onPointerDown(event: PointerEvent): void {
    if (!this.imageLoaded) {
      return;
    }

    this.dragging = true;
    this.lastPointerX = event.clientX;
    this.lastPointerY = event.clientY;
    (event.currentTarget as HTMLElement).setPointerCapture(event.pointerId);
  }

  onPointerMove(event: PointerEvent): void {
    if (!this.dragging) {
      return;
    }

    this.offsetX += event.clientX - this.lastPointerX;
    this.offsetY += event.clientY - this.lastPointerY;
    this.lastPointerX = event.clientX;
    this.lastPointerY = event.clientY;
    this.constrainOffset();
  }

  onPointerUp(event: PointerEvent): void {
    this.dragging = false;
    (event.currentTarget as HTMLElement).releasePointerCapture(event.pointerId);
  }

  onWheel(event: WheelEvent): void {
    if (!this.imageLoaded) {
      return;
    }

    event.preventDefault();
    const nextZoom = this.zoom + (event.deltaY < 0 ? 0.08 : -0.08);
    this.setZoom(nextZoom);
  }

  onZoomInput(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.setZoom(Number(input.value));
  }

  resetCrop(): void {
    this.zoom = 1;
    this.offsetX = 0;
    this.offsetY = 0;
    this.updateFrameSize();
    this.constrainOffset();
  }

  async apply(): Promise<void> {
    const image = this.cropImage?.nativeElement;
    if (!image || !this.imageLoaded) {
      return;
    }

    const scale = this.scale;
    const sourceSize = this.frameSize / scale;
    const sourceX = (this.displayWidth / 2 - this.frameSize / 2 - this.offsetX) / scale;
    const sourceY = (this.displayHeight / 2 - this.frameSize / 2 - this.offsetY) / scale;
    const canvas = document.createElement('canvas');
    canvas.width = this.outputSize;
    canvas.height = this.outputSize;
    const context = canvas.getContext('2d');

    if (!context) {
      return;
    }

    context.imageSmoothingEnabled = true;
    context.imageSmoothingQuality = 'high';
    context.drawImage(
      image,
      sourceX,
      sourceY,
      sourceSize,
      sourceSize,
      0,
      0,
      this.outputSize,
      this.outputSize,
    );

    const blob = await new Promise<Blob | null>(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.92));
    if (!blob) {
      return;
    }

    this.dialogRef.close(new File([blob], this.outputFileName, { type: 'image/jpeg' }));
  }

  close(): void {
    this.dialogRef.close(null);
  }

  private get outputFileName(): string {
    return this.data.fileName.replace(/\.[^.]+$/, '') + '-avatar.jpg';
  }

  private get baseScale(): number {
    if (!this.naturalWidth || !this.naturalHeight) {
      return 1;
    }

    return Math.max(this.frameSize / this.naturalWidth, this.frameSize / this.naturalHeight);
  }

  private get scale(): number {
    return this.baseScale * this.zoom;
  }

  private get displayWidth(): number {
    return this.naturalWidth * this.scale;
  }

  private get displayHeight(): number {
    return this.naturalHeight * this.scale;
  }

  private setZoom(value: number): void {
    this.zoom = Math.min(this.maxZoom, Math.max(this.minZoom, value));
    this.constrainOffset();
  }

  private updateFrameSize(): void {
    const nextSize = this.cropFrame?.nativeElement.clientWidth || this.frameSize;
    this.frameSize = Math.max(260, Math.round(nextSize));
  }

  private constrainOffset(): void {
    const maxX = Math.max(0, (this.displayWidth - this.frameSize) / 2);
    const maxY = Math.max(0, (this.displayHeight - this.frameSize) / 2);
    this.offsetX = Math.min(maxX, Math.max(-maxX, this.offsetX));
    this.offsetY = Math.min(maxY, Math.max(-maxY, this.offsetY));
  }
}
