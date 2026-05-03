import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';
import { MatDialogModule } from '@angular/material/dialog';
import { MatDividerModule } from '@angular/material/divider';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatIconModule } from '@angular/material/icon';
import { MatTabsModule } from '@angular/material/tabs';

interface GuideStep {
  icon: string;
  title: string;
  text: string;
}

interface StatusGuide {
  code: string;
  title: string;
  text: string;
  tone: string;
}

interface CalculationGuide {
  title: string;
  formula: string;
  note: string;
}

@Component({
  selector: 'app-help-guide-dialog',
  standalone: true,
  imports: [
    CommonModule,
    MatButtonModule,
    MatChipsModule,
    MatDialogModule,
    MatDividerModule,
    MatExpansionModule,
    MatIconModule,
    MatTabsModule,
  ],
  templateUrl: './help-guide-dialog.component.html',
  styleUrl: './help-guide-dialog.component.css',
})
export class HelpGuideDialogComponent {
  readonly workflowSteps: GuideStep[] = [
    {
      icon: 'assignment_add',
      title: 'Принять устройство',
      text: 'Создайте заказ, выберите клиента, устройство, проблему, комплектацию, состояние и ориентир стоимости.',
    },
    {
      icon: 'engineering',
      title: 'Вести ремонт по этапам',
      text: 'В карточке заказа добавляйте этапы работ: диагностика, снятие панели, пайка, тестирование. Фото можно сделать видимым клиенту.',
    },
    {
      icon: 'fact_check',
      title: 'Согласовать допработы',
      text: 'Если меняется сумма или объем ремонта, отправьте клиенту согласование. Решение сохраняется в истории заказа.',
    },
    {
      icon: 'sms',
      title: 'Дать клиенту прозрачность',
      text: 'Клиент входит по телефону и паролю, видит свои заказы, публичные этапы и текущий статус устройства.',
    },
    {
      icon: 'analytics',
      title: 'Контролировать бизнес',
      text: 'Проверяйте выручку, средний чек, статусы, склад и отчеты по филиалам без ручных таблиц.',
    },
  ];

  readonly statuses: StatusGuide[] = [
    {
      code: 'received',
      title: 'Принят',
      text: 'Устройство оформлено, проблема записана, клиент получил номер заказа.',
      tone: 'blue',
    },
    {
      code: 'diagnosed',
      title: 'Диагностирован',
      text: 'Мастер нашел причину, можно уточнять цену, срок и список работ.',
      tone: 'amber',
    },
    {
      code: 'waiting_parts',
      title: 'Ожидание запчастей',
      text: 'Ремонт упирается в поставку детали или подтверждение закупки.',
      tone: 'violet',
    },
    {
      code: 'in_repair',
      title: 'В ремонте',
      text: 'Идут работы: пайка, замена модуля, чистка, сборка или восстановление.',
      tone: 'orange',
    },
    {
      code: 'testing',
      title: 'Тестирование',
      text: 'Устройство проверяется после ремонта: зарядка, сеть, датчики, стабильность.',
      tone: 'cyan',
    },
    {
      code: 'ready',
      title: 'Готов',
      text: 'Работы завершены, устройство можно выдавать клиенту.',
      tone: 'green',
    },
    {
      code: 'completed',
      title: 'Выдан',
      text: 'Клиент забрал устройство, заказ закрыт.',
      tone: 'neutral',
    },
    {
      code: 'cancelled',
      title: 'Отменен',
      text: 'Ремонт не выполняется: отказ клиента, нерентабельность или другая причина.',
      tone: 'red',
    },
  ];

  readonly calculations: CalculationGuide[] = [
    {
      title: 'Заказы за месяц',
      formula: 'Количество заказов, попавших в текущий отчетный период.',
      note: 'Используется для загрузки приемки и мастеров.',
    },
    {
      title: 'Выручка за месяц',
      formula: 'Сумма оплат или финальных стоимостей заказов за период, если платежи еще не заведены полностью.',
      note: 'Для точной кассы подключайте оплаты и закрытие выдачи.',
    },
    {
      title: 'Средний чек',
      formula: 'Выручка за период / количество заказов за период.',
      note: 'Если заказов нет, значение считается как 0, чтобы не показывать ложную динамику.',
    },
    {
      title: 'Остаток оплаты',
      formula: 'Итоговая стоимость или оценка - предоплата.',
      note: 'Показывает, сколько нужно получить при выдаче.',
    },
    {
      title: 'Подписка',
      formula: 'Оставшиеся дни / общая длительность тарифа * 100.',
      note: 'Цветовая шкала округляется вниз по 10%: 100, 90, 80 ... 0.',
    },
  ];

  readonly subscriptionBuckets = [
    { value: '100-80%', label: 'спокойно', color: '#1b8f3a' },
    { value: '70-50%', label: 'следить', color: '#c4d137' },
    { value: '40-20%', label: 'скоро продлить', color: '#ef842f' },
    { value: '10-0%', label: 'критично', color: '#b91c1c' },
  ];
}
