export type SessionInfo = {
  id: string;
  protocol: "ssh" | "telnet";
  host: string;
  port: number;
  username: string | null;
  connected: boolean;
  created_at: string;
};

export type ConnectRequest = {
  protocol: "ssh" | "telnet";
  host: string;
  port?: number;
  username?: string;
  password?: string;
};

export type Pending = {
  id: string;
  session_id: string;
  command: string;
  risk: "read_only" | "config" | "dangerous";
  reason: string;
};

export type AgentReply = { text: string; pending: Pending[] };

export type AuditRow = {
  id: number;
  time: string;
  session_id: string;
  command: string;
  risk: string;
  decision: string;
  source: string;
};

export type AISettings = {
  ollama_url: string;
  model: string;
  approval_mode: "confirm" | "readonly_auto";
};

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

// FastAPI кладёт ошибку в поле detail: это строка, объект или список
export function errorMessage(body: unknown, fallback: string): string {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((d) => d?.msg ?? String(d)).join("; ");
  if (detail && typeof detail === "object" && "message" in detail) {
    return String((detail as { message: unknown }).message);
  }
  return fallback;
}

export function terminalUrl(sessionId: string, loc: Pick<Location, "protocol" | "host"> = window.location): string {
  const scheme = loc.protocol === "https:" ? "wss" : "ws";
  return `${scheme}://${loc.host}/api/sessions/${sessionId}/terminal`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new ApiError(response.status, errorMessage(body, `Ошибка ${response.status}`));
  }
  return response.status === 204 ? (undefined as T) : response.json();
}

const post = (body?: unknown): RequestInit => ({
  method: "POST",
  body: body === undefined ? undefined : JSON.stringify(body),
});

export const api = {
  sessions: () => request<SessionInfo[]>("/api/sessions"),
  connect: (body: ConnectRequest) => request<SessionInfo>("/api/sessions", post(body)),
  close: (id: string) => request<void>(`/api/sessions/${id}`, { method: "DELETE" }),
  chat: (id: string, message: string) =>
    request<AgentReply>(`/api/sessions/${id}/assistant`, post({ message })),
  pending: (id: string) => request<Pending[]>(`/api/sessions/${id}/pending`),
  approve: (pendingId: string) => request<AgentReply>(`/api/pending/${pendingId}/approve`, post()),
  deny: (pendingId: string) => request<AgentReply>(`/api/pending/${pendingId}/deny`, post()),
  audit: (limit = 50) => request<AuditRow[]>(`/api/audit?limit=${limit}`),
  getSettings: () => request<AISettings>("/api/ai/settings"),
  putSettings: (settings: AISettings) =>
    request<AISettings>("/api/ai/settings", { method: "PUT", body: JSON.stringify(settings) }),
};
