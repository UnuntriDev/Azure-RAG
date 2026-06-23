// Typed fetch wrapper around the FastAPI backend.

import type {
  ChatRequest,
  ConversationDetail,
  ConversationRead,
  CursorPage,
  DocumentAnalysis,
  DocumentRead,
  DocumentUploadResponse,
  PromptVersion,
  QueryLog,
  QueryRequest,
  QueryResponse,
  Source,
  TraceRead,
} from "@/types/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const isFormData = init?.body instanceof FormData;
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...init?.headers,
    },
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = (await res.json()) as { detail?: string };
      if (data?.detail) detail = data.detail;
    } catch {
      // non-JSON error body — keep statusText
    }
    throw new ApiError(res.status, detail);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

// XHR instead of fetch — fetch() has no upload.onprogress event.
async function uploadWithProgress<T>(
  path: string,
  form: FormData,
  onProgress?: (pct: number) => void,
): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_URL}${path}`);
    xhr.withCredentials = true;
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && onProgress) onProgress(Math.round((e.loaded / e.total) * 100));
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(xhr.responseText ? (JSON.parse(xhr.responseText) as T) : (undefined as T));
        return;
      }
      let detail = xhr.statusText;
      try {
        const data = JSON.parse(xhr.responseText) as { detail?: string };
        if (data?.detail) detail = data.detail;
      } catch {
        // non-JSON error body — keep statusText
      }
      reject(new ApiError(xhr.status, detail));
    };
    xhr.onerror = () => reject(new ApiError(0, "Błąd sieci podczas wysyłania."));
    xhr.send(form);
  });
}

export interface ChatStreamCallbacks {
  onConversationId: (id: string) => void;
  onTool: (name: string) => void;
  onDelta: (content: string) => void;
  onSources: (sources: Source[]) => void;
  onDone: (latencyMs: number) => void;
  onError: (detail: string) => void;
}

async function chatStream(body: ChatRequest, callbacks: ChatStreamCallbacks): Promise<void> {
  const res = await fetch(`${API_URL}/api/chat`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = (await res.json()) as { detail?: string };
      if (data?.detail) detail = data.detail;
    } catch {
      // non-JSON error body
    }
    callbacks.onError(detail);
    return;
  }

  const reader = res.body?.getReader();
  if (!reader) {
    callbacks.onError("Brak strumienia odpowiedzi.");
    return;
  }

  const decoder = new TextDecoder();
  let buffer = "";
  let currentEvent = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      if (line.startsWith("event: ")) {
        currentEvent = line.slice(7);
      } else if (line.startsWith("data: ") && currentEvent) {
        const raw = line.slice(6);
        try {
          const data = JSON.parse(raw);
          switch (currentEvent) {
            case "conversation":
              callbacks.onConversationId(data.id);
              break;
            case "tool":
              callbacks.onTool(data.name);
              break;
            case "delta":
              callbacks.onDelta(data.content);
              break;
            case "sources":
              callbacks.onSources(data as Source[]);
              break;
            case "done":
              callbacks.onDone(data.latency_ms);
              break;
            case "error":
              callbacks.onError(data.detail);
              break;
          }
        } catch {
          // malformed JSON line — skip
        }
        currentEvent = "";
      }
    }
  }
}

export const api = {
  listDocuments: () => request<CursorPage<DocumentRead>>("/api/documents").then((p) => p.items),
  getDocument: (id: string) => request<DocumentRead>(`/api/documents/${id}`),
  uploadDocument: (file: File, onProgress?: (pct: number) => void) => {
    const form = new FormData();
    form.append("file", file);
    return uploadWithProgress<DocumentUploadResponse>(
      "/api/documents/upload",
      form,
      onProgress,
    );
  },
  deleteDocument: (id: string) =>
    request<void>(`/api/documents/${id}`, { method: "DELETE" }),
  analyzeDocument: (id: string) =>
    request<DocumentAnalysis>(`/api/documents/${id}/analyze`, { method: "POST" }),
  query: (body: QueryRequest) =>
    request<QueryResponse>("/api/query", { method: "POST", body: JSON.stringify(body) }),
  queryLogs: () => request<CursorPage<QueryLog>>("/api/query/logs").then((p) => p.items),

  listPromptVersions: () => request<PromptVersion[]>("/api/prompts"),
  listTraces: () => request<CursorPage<TraceRead>>("/api/traces").then((p) => p.items),
  chatStream,
  listConversations: () => request<CursorPage<ConversationRead>>("/api/chat").then((p) => p.items),
  getConversation: (id: string) => request<ConversationDetail>(`/api/chat/${id}`),
  deleteConversation: (id: string) =>
    request<void>(`/api/chat/${id}`, { method: "DELETE" }),
};
