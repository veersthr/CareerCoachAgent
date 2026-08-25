import { useState } from "react";
import { submitJdPdf, submitJdText } from "../api/client";

const MODE_TEXT = "text";
const MODE_PDF = "pdf";

export default function JdInput({ onResult }) {
  const [mode, setMode] = useState(MODE_TEXT);
  const [jdText, setJdText] = useState("");
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit(event) {
    event.preventDefault();
    setError(null);

    if (mode === MODE_TEXT && !jdText.trim()) {
      setError("Paste a job description first.");
      return;
    }
    if (mode === MODE_PDF && !file) {
      setError("Choose a PDF file first.");
      return;
    }

    setLoading(true);
    try {
      const result =
        mode === MODE_TEXT ? await submitJdText(jdText) : await submitJdPdf(file);
      onResult(result);
    } catch (err) {
      setError(err.message || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form className="jd-input" onSubmit={handleSubmit}>
      <div className="jd-input__mode-toggle">
        <button
          type="button"
          className={mode === MODE_TEXT ? "active" : ""}
          onClick={() => setMode(MODE_TEXT)}
        >
          Paste text
        </button>
        <button
          type="button"
          className={mode === MODE_PDF ? "active" : ""}
          onClick={() => setMode(MODE_PDF)}
        >
          Upload PDF
        </button>
      </div>

      {mode === MODE_TEXT ? (
        <textarea
          rows={10}
          placeholder="Paste the job description here..."
          value={jdText}
          onChange={(e) => setJdText(e.target.value)}
        />
      ) : (
        <input
          type="file"
          accept="application/pdf"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
      )}

      {error && <p className="jd-input__error">{error}</p>}

      <button type="submit" disabled={loading}>
        {loading ? "Building your roadmap..." : "Generate Roadmap"}
      </button>
    </form>
  );
}
