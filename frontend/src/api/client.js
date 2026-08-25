// Thin REST client for api.py's three endpoints. No axios — fetch is enough.

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function handleResponse(response) {
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail || detail;
    } catch {
      // response wasn't JSON — fall back to statusText
    }
    throw new Error(`API error ${response.status}: ${detail}`);
  }
  return response.json();
}

/** POST /roadmap/text — jdText: string. Returns { session_id, report_markdown, state }. */
export async function submitJdText(jdText) {
  const response = await fetch(`${API_BASE_URL}/roadmap/text`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ jd_text: jdText }),
  });
  return handleResponse(response);
}

/** POST /roadmap/pdf — file: File. Returns { session_id, report_markdown, state }. */
export async function submitJdPdf(file) {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(`${API_BASE_URL}/roadmap/pdf`, {
    method: "POST",
    body: formData,
  });
  return handleResponse(response);
}

/** GET /session/{id} — returns the previously-saved session payload. */
export async function getSession(sessionId) {
  const response = await fetch(`${API_BASE_URL}/session/${encodeURIComponent(sessionId)}`);
  return handleResponse(response);
}
