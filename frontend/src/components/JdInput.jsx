import { useEffect, useRef, useState } from "react";
import { submitJdPdf, submitJdText } from "../api/client";

const MODE_TEXT = "text";
const MODE_PDF = "pdf";

const STAGES = [
  "Reading the job description…",
  "Extracting the core skills…",
  "Mapping skills to a 6-week schedule…",
  "Lining up learning resources…",
  "Validating the roadmap…",
];

function StagedLoader() {
  const [stageIndex, setStageIndex] = useState(0);
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const stageTimer = setInterval(() => {
      setStageIndex((i) => Math.min(i + 1, STAGES.length - 1));
    }, 3200);
    const clock = setInterval(() => setElapsed((s) => s + 1), 1000);
    return () => {
      clearInterval(stageTimer);
      clearInterval(clock);
    };
  }, []);

  return (
    <div className="staged-loader" role="status" aria-live="polite">
      <div className="staged-loader__header">
        <span className="staged-loader__spinner" aria-hidden="true" />
        <div>
          <p className="staged-loader__title">Building your roadmap</p>
          <p className="staged-loader__elapsed">{elapsed}s — this can take a minute</p>
        </div>
      </div>
      <ol className="staged-loader__stages">
        {STAGES.map((stage, i) => {
          const state = i < stageIndex ? "done" : i === stageIndex ? "active" : "pending";
          return (
            <li key={stage} className={`staged-loader__stage staged-loader__stage--${state}`}>
              <span className="staged-loader__dot" aria-hidden="true">
                {state === "done" ? "✓" : ""}
              </span>
              {stage}
            </li>
          );
        })}
      </ol>
    </div>
  );
}

export default function JdInput({ onResult }) {
  const [mode, setMode] = useState(MODE_TEXT);
  const [jdText, setJdText] = useState("");
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const errorRef = useRef(null);

  useEffect(() => {
    if (error && errorRef.current) {
      errorRef.current.focus();
    }
  }, [error]);

  async function handleSubmit(event) {
    event.preventDefault();
    setError(null);

    if (mode === MODE_TEXT && !jdText.trim()) {
      setError("Paste a job description before generating a roadmap.");
      return;
    }
    if (mode === MODE_PDF && !file) {
      setError("Choose a PDF file before generating a roadmap.");
      return;
    }

    setLoading(true);
    try {
      const result =
        mode === MODE_TEXT ? await submitJdText(jdText) : await submitJdPdf(file);
      onResult(result);
    } catch (err) {
      setError(
        err.message ||
          "Something went wrong reaching the roadmap service. Check your connection and try again."
      );
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <section className="input-card">
        <StagedLoader />
      </section>
    );
  }

  return (
    <section className="input-card">
      <form className="jd-input" onSubmit={handleSubmit}>
        <div className="input-card__eyebrow">
          <span className="step-badge">1</span>
          <span>Start with a job description</span>
        </div>

        <div className="jd-input__mode-toggle" role="tablist" aria-label="Job description input method">
          <button
            type="button"
            role="tab"
            aria-selected={mode === MODE_TEXT}
            className={mode === MODE_TEXT ? "active" : ""}
            onClick={() => setMode(MODE_TEXT)}
          >
            Paste text
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={mode === MODE_PDF}
            className={mode === MODE_PDF ? "active" : ""}
            onClick={() => setMode(MODE_PDF)}
          >
            Upload PDF
          </button>
        </div>

        {mode === MODE_TEXT ? (
          <textarea
            rows={10}
            placeholder="Paste the job description here…"
            value={jdText}
            onChange={(e) => setJdText(e.target.value)}
            aria-label="Job description text"
          />
        ) : (
          <label className="jd-input__file">
            <input
              type="file"
              accept="application/pdf"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
            <span>{file ? file.name : "Choose a PDF file…"}</span>
          </label>
        )}

        {error && (
          <p className="jd-input__error" ref={errorRef} tabIndex={-1}>
            {error}
          </p>
        )}

        <button type="submit" className="button-primary" disabled={loading}>
          Generate roadmap
        </button>
      </form>
    </section>
  );
}
