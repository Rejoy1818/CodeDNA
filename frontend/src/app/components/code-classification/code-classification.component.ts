import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';

@Component({
  selector: 'app-code-classification',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="cn-page-header">
      <h1 class="cn-page-title">AI vs Human Code Classification</h1>
      <p class="cn-page-subtitle">Estimate whether a code sample is human-written or AI-generated.</p>
    </div>

    <div class="cn-card">
      <div class="cn-section">
        <h2 class="cn-section-title">Train Classifier (Optional)</h2>
        <div class="cn-form-group">
          <label class="cn-form-label">Code Samples (one per line)</label>
          <textarea class="cn-input cn-textarea" rows="4" [(ngModel)]="trainSamples" name="trainSamples"></textarea>
        </div>
        <div class="cn-form-group">
          <label class="cn-form-label">Labels (1=AI, 0=Human, one per line)</label>
          <textarea class="cn-input cn-textarea" rows="4" [(ngModel)]="trainLabels" name="trainLabels"></textarea>
        </div>
        <button class="cn-btn cn-btn-secondary" (click)="trainClassifier()" [disabled]="training">Train Model</button>
        <div *ngIf="trainResult" class="cn-state-box cn-state-info">
          Accuracy: {{ trainResult.metrics?.accuracy | number:'1.2-2' }} |
          Precision: {{ trainResult.metrics?.precision | number:'1.2-2' }} |
          Recall: {{ trainResult.metrics?.recall | number:'1.2-2' }} |
          F1: {{ trainResult.metrics?.f1_score | number:'1.2-2' }}
        </div>
      </div>

      <div class="cn-section">
        <h2 class="cn-section-title">Classify a Code Sample</h2>
        <div class="cn-form-group">
          <label class="cn-form-label">Source Code</label>
          <textarea class="cn-input cn-textarea" rows="6" [(ngModel)]="codeInput" name="codeInput"></textarea>
        </div>
        <button class="cn-btn cn-btn-accent" (click)="predictCode()" [disabled]="classifying">Classify</button>
      </div>

      <div *ngIf="prediction" class="cn-result-card">
        <h5>Result</h5>
        <span class="cn-chip cn-chip-binary">{{ prediction.is_ai_generated ? 'AI-Generated' : 'Human-Written' }}</span>
        <span class="cn-chip cn-chip-confidence">{{ (prediction.confidence * 100).toFixed(1) }}% confidence</span>
        <p class="cn-text-sm cn-text-muted">{{ prediction.note }}</p>
        <div>
          <strong class="cn-text-sm">Probabilities:</strong>
          <ul class="cn-probability-list">
            <li *ngFor="let p of predictionProbabilities">{{ p.key }}: {{ (p.value * 100).toFixed(1) }}%</li>
          </ul>
        </div>
      </div>

      <div *ngIf="error" class="cn-state-box cn-state-error">{{ error }}</div>
    </div>
  `,
})
export class CodeClassificationComponent {
  trainSamples = '';
  trainLabels = '';
  training = false;
  trainResult: any = null;

  codeInput = '';
  classifying = false;
  prediction: any = null;
  predictionProbabilities: { key: string; value: number }[] = [];
  error: string | null = null;

  constructor(private api: ApiService) {}

  trainClassifier() {
    const samples = this.trainSamples.split('\n').map(s => s.trim()).filter(Boolean);
    const labels = this.trainLabels.split('\n').map(s => parseInt(s.trim(), 10)).filter(n => !isNaN(n));

    if (samples.length !== labels.length || samples.length === 0) {
      this.error = 'Samples and labels must be non-empty and equal length';
      return;
    }

    this.training = true;
    this.error = null;

    this.api.trainClassifier({ samples, labels }).subscribe({
      next: (r) => {
        this.trainResult = r;
        this.training = false;
      },
      error: () => {
        this.error = 'Training failed';
        this.training = false;
      },
    });
  }

  predictCode() {
    if (!this.codeInput.trim()) {
      this.error = 'Please enter code';
      return;
    }

    this.classifying = true;
    this.error = null;
    this.prediction = null;

    this.api.predictCode({ code: this.codeInput }).subscribe({
      next: (r) => {
        this.prediction = r;
        this.predictionProbabilities = Object.entries(r.probabilities).map(([k, v]) => ({ key: k, value: v }));
        this.classifying = false;
      },
      error: () => {
        this.error = 'Classification failed (model may not be trained yet)';
        this.classifying = false;
      },
    });
  }
}