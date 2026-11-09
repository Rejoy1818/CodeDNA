import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

const API_BASE = environment.apiBaseUrl;

export interface Repository {
  id: number;
  name: string;
  owner: string;
  description?: string;
  language?: string;
  created_at?: string;
  last_collected?: string;
}

export interface CollectRequest {
  owner: string;
  repo: string;
  max_commits?: number;
}

export interface FeatureData {
  commits_per_day: number;
  active_days: number;
  weekend_activity: number;
  avg_commits_per_week: number;
  time_of_day_distribution: Record<string, number>;
  avg_gap_between_commits_hours: number;
  code_change_volume: number;
  total_commits: number;
}

export interface AnomalyResult {
  is_anomaly: boolean;
  anomaly_score: number;
}

export interface NLPResult {
  message_features: Record<string, unknown>;
  trends: Array<Record<string, unknown>>;
}

export interface ProductivityIndicator {
  commits_per_day: number;
  avg_code_changes_per_commit: number;
  active_day_ratio: number;
  consistency_score: number;
  total_commits: number;
  active_days: number;
  total_days: number;
}

export interface ProductivityOverTime {
  period: string;
  commits: number;
  total_changes: number;
  active_authors: number;
  avg_changes_per_commit: number;
}

export interface ProductivityResult {
  indicators: ProductivityIndicator;
  over_time: ProductivityOverTime[];
}

export interface ClassifyTrainRequest {
  samples: string[];
  labels: number[];
}

export interface ClassifyTrainResponse {
  message: string;
  metrics: Record<string, unknown>;
}

export interface ClassifyPredictRequest {
  code: string;
}

export interface ClassifyPredictResult {
  is_ai_generated: boolean;
  confidence: number;
  probabilities: Record<string, number>;
}

export interface DashboardData {
  repository: Repository;
  features: FeatureData;
  nlp: NLPResult;
  productivity: ProductivityResult;
  timeline: Record<string, number>;
}

@Injectable({
  providedIn: 'root',
})
export class ApiService {
  constructor(private http: HttpClient) {}

  health(): Observable<{ status: string; service: string }> {
    return this.http.get<{ status: string; service: string }>(
      `${API_BASE}/health`
    );
  }

  collectRepository(body: CollectRequest): Observable<unknown> {
    return this.http.post(`${API_BASE}/repositories/collect`, body);
  }

  listRepositories(): Observable<Repository[]> {
    return this.http.get<Repository[]>(`${API_BASE}/repositories`);
  }

  getFeatures(repoId: number): Observable<FeatureData> {
    return this.http.get<FeatureData>(
      `${API_BASE}/repositories/${repoId}/features`
    );
  }

  detectAnomalies(repoId: number): Observable<AnomalyResult> {
    return this.http.get<AnomalyResult>(
      `${API_BASE}/repositories/${repoId}/anomalies`
    );
  }

  getNLP(repoId: number): Observable<NLPResult> {
    return this.http.get<NLPResult>(
      `${API_BASE}/repositories/${repoId}/nlp`
    );
  }

  getProductivity(repoId: number): Observable<ProductivityResult> {
    return this.http.get<ProductivityResult>(
      `${API_BASE}/repositories/${repoId}/productivity`
    );
  }

  getDashboard(repoId: number): Observable<DashboardData> {
    return this.http.get<DashboardData>(`${API_BASE}/dashboard/${repoId}`);
  }

  trainClassifier(body: ClassifyTrainRequest): Observable<ClassifyTrainResponse> {
    return this.http.post<ClassifyTrainResponse>(
      `${API_BASE}/classify/train`,
      body
    );
  }

  predictCode(body: ClassifyPredictRequest): Observable<ClassifyPredictResult> {
    return this.http.post<ClassifyPredictResult>(
      `${API_BASE}/classify/predict`,
      body
    );
  }
}
