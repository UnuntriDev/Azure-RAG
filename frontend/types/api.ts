export interface CursorPage<T> {
  items: T[];
  next_cursor: string | null;
}

export type DocumentStatus = "pending" | "processing" | "indexed" | "failed";

export interface DocumentRead {
  id: string;
  filename: string;
  status: DocumentStatus;
  chunk_count: number | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentUploadResponse {
  id: string;
  filename: string;
  status: DocumentStatus;
}

export interface QueryRequest {
  question: string;
}

export interface Source {
  document_id: string;
  filename: string;
  page: number;
  location: string; // citation label: PDF "s. 5" / Excel "arkusz X, w. 10–60" / Word "sekcja: …"
  chunk_index: number;
  score: number;
  content: string;
}

export interface QueryResponse {
  answer: string;
  sources: Source[];
  latency_ms: number;
}

export interface QueryLog {
  id: string;
  question: string;
  answer: string;
  sources: Source[];
  latency_ms: number;
  prompt_version: string;
  created_at: string;
}

export interface Entity {
  name: string;
  type: string;
}

export interface DocumentAnalysis {
  summary: string;
  key_points: string[];
  entities: Entity[];
  suggested_questions: string[];
}

export interface ChatRequest {
  question: string;
  conversation_id?: string | null;
  agent?: boolean;
  prompt_version?: string;
  document_ids?: string[] | null; // null = all docs
}

export interface PromptVersion {
  id: string;
  label: string;
  description: string;
  default: boolean;
}

export interface MessageRead {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources: Source[] | null;
  latency_ms: number | null;
  created_at: string;
}

export interface ConversationRead {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
}

export interface ConversationDetail extends ConversationRead {
  messages: MessageRead[];
}

export interface TraceSpan {
  name: string;
  duration_ms: number;
  meta: Record<string, unknown>;
}

export interface TraceRead {
  id: string;
  correlation_id: string | null;
  kind: string; // "agent" | "rag"
  question: string;
  prompt_version: string;
  spans: TraceSpan[];
  total_ms: number;
  created_at: string;
}

// SSE event types
export type ChatSSEEvent =
  | { event: "conversation"; data: { id: string } }
  | { event: "tool"; data: { name: string } }
  | { event: "delta"; data: { content: string } }
  | { event: "sources"; data: Source[] }
  | { event: "done"; data: { latency_ms: number } }
  | { event: "error"; data: { detail: string } };
