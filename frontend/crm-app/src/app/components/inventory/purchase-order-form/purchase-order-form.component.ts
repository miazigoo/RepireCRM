import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
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
  InventoryService,
  Supplier
} from '../../../services/inventory.service';

@Component({
  selector: 'app-purchase-order-form',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
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
  styleUrl: './purchase-order-form.component.css'
})
export class PurchaseOrderFormComponent implements OnInit {
  loading = false;
  suppliers: Supplier[] = [];
  items: InventoryItem[] = [];

  form: FormGroup;

  constructor(
    private fb: FormBuilder,
    private inventoryService: InventoryService,
    private router: Router,
    private snackBar: MatSnackBar
  ) {
    this.form = this.fb.group({
      supplier_id: [null as number | null],
      supplier_name: [''],
      item_id: [null as number | null, Validators.required],
      quantity: [1, [Validators.required, Validators.min(1)]],
      unit_price: [0, [Validators.required, Validators.min(0)]],
      notes: ['']
    });
  }

  ngOnInit(): void {
    this.inventoryService.getSuppliers().subscribe((suppliers) => {
      this.suppliers = suppliers;
    });

    this.inventoryService.getInventoryItems().subscribe((items) => {
      this.items = items;
    });
  }

  onItemSelected(itemId: number): void {
    const item = this.items.find(candidate => candidate.id === itemId);
    if (item) {
      this.form.patchValue({ unit_price: Number(item.purchase_price || 0) });
    }
  }

  save(): void {
    const supplierName = (this.form.get('supplier_name')?.value || '').trim();
    const supplierId = this.form.get('supplier_id')?.value;
    if (!supplierId && !supplierName) {
      this.snackBar.open('Укажите поставщика', 'Закрыть', { duration: 3000 });
      return;
    }

    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    const value = this.form.getRawValue();
    this.loading = true;
    this.inventoryService.createPurchaseOrder({
      supplier_id: supplierId || undefined,
      supplier_name: supplierName || undefined,
      notes: (value.notes || '').trim(),
      items: [
        {
          item_id: Number(value.item_id),
          quantity: Number(value.quantity),
          unit_price: Number(value.unit_price)
        }
      ]
    }).subscribe({
      next: (result) => {
        const orderNumber = result?.order_number ? ` ${result.order_number}` : '';
        this.snackBar.open(`Заказ поставщику создан${orderNumber}`, 'Закрыть', {
          duration: 3000
        });
        this.router.navigate(['/inventory']);
      },
      error: (error) => {
        const message = error?.error?.error || 'Не удалось создать заказ поставщику';
        this.snackBar.open(message, 'Закрыть', { duration: 4000 });
        this.loading = false;
      }
    });
  }

  cancel(): void {
    this.router.navigate(['/inventory']);
  }
}
