import type {
  AnalyzeRequest,
  AnalyzeResponse,
  AnalyticsData,
  ClassificationFeedbackPayload,
  FeedbackRequest,
  HistoryPayload,
  RespondRequest,
  RespondResponse,
  TemplateFeedbackPayload,
} from "../types";

const envBaseUrl = import.meta.env.VITE_API_BASE_URL;
const BASE_URL = envBaseUrl && envBaseUrl.length > 0 ? envBaseUrl : "http://localhost:8000";

export class ApiError extends Error {
  status?: number;

  constructor(message: string, status?: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, init: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new ApiError(detail || response.statusText, response.status);
  }

  return (await response.json()) as T;
}

export async function analyze(payload: AnalyzeRequest): Promise<AnalyzeResponse> {
  return request<AnalyzeResponse>("/analyze", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function respond(payload: RespondRequest): Promise<RespondResponse> {
  return request<RespondResponse>("/respond", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function feedback(payload: FeedbackRequest): Promise<void> {
  await request("/feedback", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getAnalytics(): Promise<AnalyticsData> {
  return request<AnalyticsData>("/analytics", { method: "GET" });
}

export async function sendClassificationFeedback(
  payload: ClassificationFeedbackPayload,
): Promise<AnalyticsData> {
  return request<AnalyticsData>("/metrics/classification", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function sendTemplateFeedback(
  payload: TemplateFeedbackPayload,
): Promise<AnalyticsData> {
  return request<AnalyticsData>("/metrics/template", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function submitHistory(payload: HistoryPayload): Promise<AnalyticsData> {
  return request<AnalyticsData>("/history", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

