export type EntityMap = Record<string, string>;

export interface Recommendation {
  id: number;
  category: string;
  subcategory: string;
  audience: string | null;
  question: string;
  answer: string;
  score: number;
}

export interface AnalyzeResponse {
  category: string;
  category_confidence: number;
  subcategory: string;
  subcategory_confidence: number;
  confidence: number;
  entities: EntityMap;
  products: string[];
  recommendations: Recommendation[];
}

export interface AnalyzeRequest {
  text: string;
}

export interface RespondRequest {
  template: string;
  entities: EntityMap;
}

export interface RespondResponse {
  answer: string;
}

export interface FeedbackRequest {
  query: string;
  category?: string | null;
  subcategory?: string | null;
  selected_template_id?: number | null;
  final_answer: string;
  is_helpful: boolean;
  notes?: string | null;
}

export interface ClassificationFeedbackPayload {
  category: string;
  subcategory: string;
  is_correct: boolean;
}

export interface TemplateFeedbackPayload {
  is_positive: boolean;
}

export interface HistoryPayload {
  query: string;
  category?: string | null;
  subcategory?: string | null;
  template_id?: number | null;
  final_answer: string;
}

export interface ClassificationStat {
  category: string;
  subcategory: string;
  correct: number;
  incorrect: number;
  accuracy: number;
}

export interface TemplateStats {
  positive: number;
  negative: number;
  accuracy: number;
}

export interface HistoryItem {
  id: number;
  query: string;
  category: string;
  subcategory: string;
  template_id?: number | null;
  final_answer: string;
  created_at: string;
}

export interface AnalyticsData {
  classification: ClassificationStat[];
  template: TemplateStats;
  history: HistoryItem[];
}
