import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { HelpGuideDialogComponent } from './help-guide-dialog.component';

describe('HelpGuideDialogComponent', () => {
  let fixture: ComponentFixture<HelpGuideDialogComponent>;
  let component: HelpGuideDialogComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [HelpGuideDialogComponent],
      providers: [provideNoopAnimations()],
    }).compileComponents();

    fixture = TestBed.createComponent(HelpGuideDialogComponent);
    component = fixture.componentInstance;
  });

  it('renders the CRM guide modal', () => {
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;

    expect(compiled.querySelector('h2')?.textContent).toContain(
      'Как работать и где что считается'
    );
  });

  it('documents workflow, statuses and calculations', () => {
    expect(component.workflowSteps.length).toBeGreaterThanOrEqual(5);
    expect(component.statuses.map((status) => status.code)).toContain('in_repair');
    expect(component.calculations.map((item) => item.title)).toContain('Средний чек');
    expect(component.subscriptionBuckets.length).toBe(4);
  });
});
