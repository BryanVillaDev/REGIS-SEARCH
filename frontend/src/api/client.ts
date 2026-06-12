export type UserPublic = {
  id: string;
  username: string;
  role: string;
  is_active: boolean;
};

export type LoginResponse = {
  access_token: string;
  token_type: string;
  user: UserPublic;
};

export type LocationInfo = {
  code?: string | null;
  ciudad?: string | null;
  depto?: string | null;
};

export type ContactInfo = {
  cedula: string;
  cel?: string | null;
  nombre?: string | null;
  dir?: string | null;
  ciud?: string | null;
};

export type RecordDetail = {
  aninuip: number;
  full_name: string;
  identity: Record<string, unknown>;
  locations: Record<string, LocationInfo | null>;
  contacts: ContactInfo[];
  raw: Record<string, unknown>;
};

export type NameSearchItem = {
  aninuip: number;
  apellido1: string;
  apellido2?: string | null;
  nombre1: string;
  nombre2?: string | null;
  full_name: string;
  fecha_nacimiento?: string | null;
  sexo?: string | null;
  lugar_nacimiento?: LocationInfo | null;
};

export type NameSearchResponse = {
  items: NameSearchItem[];
  limit: number;
  offset: number;
  has_more: boolean;
};

export type JobPublic = {
  id: string;
  kind: string;
  status: string;
  input_count: number;
  unique_count: number;
  processed_count: number;
  result_count: number;
  error?: string | null;
  has_csv: boolean;
  has_xlsx: boolean;
  created_at: string;
  updated_at: string;
  started_at?: string | null;
  finished_at?: string | null;
};

const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api";
const TOKEN_KEY = "regis_token";

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token: string | null) {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

type ApiOptions = RequestInit & {
  auth?: boolean;
};

async function apiFetch<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const token = getStoredToken();
  const headers = new Headers(options.headers);

  if (!(options.body instanceof FormData) && options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (options.auth !== false && token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers
  });

  if (response.status === 401) {
    setStoredToken(null);
  }

  if (!response.ok) {
    let message = "La solicitud fallo";
    try {
      const body = await response.json();
      message = body.detail || message;
    } catch {
      message = await response.text();
    }
    throw new Error(message);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export function login(username: string, password: string) {
  return apiFetch<LoginResponse>("/auth/login", {
    method: "POST",
    auth: false,
    body: JSON.stringify({ username, password })
  });
}

export function getMe() {
  return apiFetch<UserPublic>("/auth/me");
}

export function getRecord(aninuip: string) {
  return apiFetch<RecordDetail>(`/records/${encodeURIComponent(aninuip)}`);
}

export type NameSearchParams = {
  apellido1?: string;
  apellido2?: string;
  nombre1?: string;
  nombre2?: string;
  mode?: "prefix" | "exact";
  limit?: number;
  offset?: number;
};

export function searchName(params: NameSearchParams) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && String(value).trim() !== "") {
      query.set(key, String(value));
    }
  });
  return apiFetch<NameSearchResponse>(`/search/name?${query.toString()}`);
}

export function createCedulasJob(cedulas: string) {
  return apiFetch<JobPublic>("/search/cedulas", {
    method: "POST",
    body: JSON.stringify({ cedulas })
  });
}

export function createNombresJob(nombres: string) {
  return apiFetch<JobPublic>("/search/nombres", {
    method: "POST",
    body: JSON.stringify({ nombres })
  });
}

export function listJobs() {
  return apiFetch<JobPublic[]>("/jobs");
}

export async function downloadJob(jobId: string, format: "csv" | "xlsx") {
  const token = getStoredToken();
  const response = await fetch(`${API_BASE}/jobs/${jobId}/download?format=${format}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : undefined
  });
  if (!response.ok) {
    throw new Error("Archivo no disponible");
  }
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `regis-${jobId}.${format}`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.URL.revokeObjectURL(url);
}
