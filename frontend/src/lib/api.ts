import type {
  AnalyzeRequest,
  AnalyzeResponse,
  FeedbackRequest,
  RespondRequest,
  RespondResponse,
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

