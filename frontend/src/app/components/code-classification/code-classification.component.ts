import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';

@Component({
  selector: 'app-code-classification',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="card">
      <div class="card-body">
        <h2 class="card-title mb-4">AI vs Human Code Classification</h2>
        <p class="text-muted">
          Estimate whether a code sample is human-written or AI-generated.
          <strong>This is an estimate, not proof of authorship.</strong>
        </p>

        <div class="mb-4">
          <h5>Train Classifier (Optional)</h5>
          <div class="mb-3">
            <label class="form-label">Code Samples (one per line)</label>
            <textarea class="form-control" rows="4" [(ngModel)]="trainSamples" name="trainSamples"></textarea>
          </div>
          <div class="mb-3">
            <label class="form-label">Labels (1=AI, 0=Human, one per line)</label>
            <textarea class="form-control" rows="4" [(ngModel)]="trainLabels" name="trainLabels"></textarea>
          </div>
          <button class="btn btn-outline-primary" (click)="trainClassifier()" [disabled]="training">Train Model</button>
          <div *ngIf="trainResult" class="mt-3 alert alert-info">
            Accuracy: {{ trainResult.metrics?.accuracy | number:'1.2-2' }} |
            Precision: {{ trainResult.metrics?.precision | number:'1.2-2' }} |
            Recall: {{ trainResult.metrics?.recall | number:'1.2-2' }} |
            F1: {{ trainResult.metrics?.f1_score | number:'1.2-2' }}
          </div>
        </div>

        <div class="mb-4">
          <h5>Classify a Code Sample</h5>
          <div class="mb-3">
            <label class="form-label">Source Code</label>
            <textarea class="form-control" rows="6" [(ngModel)]="codeInput" name="codeInput"></textarea>
          </div>
          <button class="btn btn-primary" (click)="predictCode()" [disabled]="classifying">Classify</button>
        </div>

        <div *ngIf="prediction" class="mt-4 alert alert-info">
          <h5>Result</h5>
          <p><strong>Prediction:</strong> {{ prediction.is_ai_generated ? 'AI-Generated' : 'Human-Written' }}</p>
          <p><strong>Confidence:</strong> {{ (prediction.confidence * 100).toFixed(1) }}%</p>
          <p class="text-muted small">{{ prediction.note }}</p>
          <div>
            <strong>Probabilities:</strong>
            <ul class="list-unstyled">
              <li *ngFor="let p of predictionProbabilities">Class {{ p.key }}: {{ (p.value * 100).toFixed(1) }}%</li>
            </ul>
          </div>
        </div>

        <div *ngIf="error" class="mt-4 alert alert-danger">{{ error }}</div>
      </div>
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