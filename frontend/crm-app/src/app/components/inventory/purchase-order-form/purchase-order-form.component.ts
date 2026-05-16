import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { FormArray, FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import {
  InventoryItem,
  InventoryProductGroup,
  InventoryService,
  Supplier
} from '../../../services/inventory.service';

@Component({
  selector: 'app-purchase-order-form',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatAutocompleteModule,
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatSelectModule,
    MatSnackBarModule
  ],
  templateUrl: './purchase-order-form.component.html',
  styleUrl: './purchase-order-form.component.scss'
})
export class PurchaseOrderFormComponent implements OnInit {
  loading = false;
  suppliers: Supplier[] = [];
  productGroups: InventoryProductGroup[] = [];
  items: InventoryItem[] = [];
  private preselectedItemId: number | null = null;

  readonly priorities = [
    { value: 'normal', label: 'Обычный' },
    { value: 'high', label: 'Высокий' },
    { value: 'urgent', label: 'Срочный' },
    { value: 'low', label: 'Низкий' }
  ];

  form: FormGroup;

  constructor(
    private fb: FormBuilder,
    private inventoryService: InventoryService,
    private route: ActivatedRoute,
    private router: Router,
    private snackBar: MatSnackBar
  ) {
    this.form = this.fb.group({
      priority: ['normal', Validators.required],
      due_date: [''],
      notes: [''],
      items: this.fb.array([])
    });
  }

  ngOnInit(): void {
    const itemId = Number(this.route.snapshot.queryParamMap.get('item_id'));
    this.preselectedItemId = Number.isFinite(itemId) && itemId > 0 ? itemId : null;

    this.inventoryService.getSuppliers().subscribe((suppliers) => {
      this.suppliers = suppliers;
    });
    this.inventoryService.getProductGroups().subscribe((groups) => {
      this.productGroups = groups;
    });
    this.inventoryService.getInventoryItems().subscribe((items) => {
      this.items = items;
      this.addLine(this.preselectedItemId || undefined);
      this.preselectedItemId = null;
    });
  }

  get lines(): FormArray {
    return this.form.get('items') as FormArray;
  }

  addLine(itemId?: number): void {
    const item = itemId ? this.items.find(candidate => candidate.id === itemId) : null;
    const line = this.fb.group({
      item_id: [item?.id ?? null, Validators.required],
      quantity: [1, [Validators.required, Validators.min(1)]],
      unit_price: [Number(item?.purchase_price || 0), [Validators.required, Validators.min(0)]],
      supplier_id: [item?.primary_supplier_id ?? null],
      supplier_name: [''],
      procurement_group_name: [item?.procurement_group_name || ''],
      notes: ['']
    });
    this.lines.push(line);
  }

  removeLine(index: number): void {
    if (this.lines.length <= 1) {
      this.lines.at(0).reset({
        item_id: null,
        quantity: 1,
        unit_price: 0,
        supplier_id: null,
        supplier_name: '',
        procurement_group_name: '',
        notes: ''
      });
      return;
    }
    this.lines.removeAt(index);
  }

  onItemSelected(index: number, itemId: number): void {
    const item = this.items.find(candidate => candidate.id === itemId);
    if (!item) return;
    this.lines.at(index).patchValue({
      unit_price: Number(item.purchase_price || 0),
      supplier_id: item.primary_supplier_id ?? null,
      supplier_name: '',
      procurement_group_name: item.procurement_group_name || item.category_name || ''
    });
  }

  onSupplierSelected(index: number, supplierId: number | null): void {
    if (!supplierId) return;
    this.lines.at(index).patchValue({ supplier_name: '' });
  }

  onSupplierNameInput(index: number): void {
    const line = this.lines.at(index);
    const supplierName = String(line.get('supplier_name')?.value || '').trim();
    if (!supplierName || !line.get('supplier_id')?.value) return;
    line.patchValue({ supplier_id: null }, { emitEvent: false });
  }

  save(asDraft = false): void {
    const value = this.form.getRawValue();
    const selectedItemIds = this.lines.controls
      .map((line) => Number(line.get('item_id')?.value || 0))
      .filter((itemId: number) => itemId > 0);
    const duplicateItemId = this.findDuplicateItemId(selectedItemIds);
    if (duplicateItemId) {
      const item = this.items.find(candidate => candidate.id === duplicateItemId);
      this.snackBar.open(
        `Товар ${item?.name || duplicateItemId} уже есть в заявке`,
        'Закрыть',
        { duration: 3500 }
      );
      return;
    }

    if (this.form.invalid || this.lines.length === 0) {
      this.form.markAllAsTouched();
      return;
    }

    const requestItems = value.items
      .map((line: any) => ({
        item_id: Number(line.item_id),
        quantity: Number(line.quantity || 0),
        unit_price: Number(line.unit_price || 0),
        supplier_id: line.supplier_id || null,
        supplier_name: String(line.supplier_name || '').trim() || undefined,
        procurement_group_name: String(line.procurement_group_name || '').trim() || undefined,
        notes: String(line.notes || '').trim()
      }))
      .filter((line: any) => line.item_id && line.quantity > 0);

    if (requestItems.length === 0) {
      this.snackBar.open('Добавьте хотя бы одну позицию', 'Закрыть', { duration: 3000 });
      return;
    }

    this.loading = true;
    this.inventoryService.createPurchaseRequest({
      priority: value.priority || 'normal',
      due_date: value.due_date || null,
      notes: String(value.notes || '').trim(),
      as_draft: asDraft,
      items: requestItems
    }).subscribe({
      next: (result) => {
        this.snackBar.open(`Заявка ${result.request_number} создана`, 'Закрыть', {
          duration: 3000
        });
        this.router.navigate(['/inventory/purchase-requests']);
      },
      error: (error) => {
        const message = error?.error?.error || 'Не удалось создать заявку';
        this.snackBar.open(message, 'Закрыть', { duration: 4000 });
        this.loading = false;
      }
    });
  }

  cancel(): void {
    this.router.navigate(['/inventory']);
  }

  private findDuplicateItemId(itemIds: number[]): number | null {
    const seen = new Set<number>();
    for (const itemId of itemIds) {
      if (seen.has(itemId)) return itemId;
      seen.add(itemId);
    }
    return null;
  }
}
