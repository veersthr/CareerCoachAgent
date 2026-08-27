import { useState } from "react";
import JdInput from "./components/JdInput";
import RoadmapTabs from "./components/RoadmapTabs";
import "./App.css";

export default function App() {
  const [result, setResult] = useState(null);

  return (
    <div className="app">
      <header className="app__header">
        <div className="app__eyebrow-row">
          <svg
            className="app__logo-icon"
            width="19"
            height="19"
            viewBox="0 0 20 20"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            aria-hidden="true"
          >
            <defs>
              <linearGradient id="logoGradient" x1="0" y1="0" x2="20" y2="20" gradientUnits="userSpaceOnUse">
                <stop offset="0" stopColor="var(--color-evergreen)" />
                <stop offset="1" stopColor="var(--color-evergreen-dark)" />
              </linearGradient>
            </defs>
            <rect width="20" height="20" rx="6" fill="url(#logoGradient)" />
            <rect x="5" y="12.5" width="2.6" height="4.5" rx="1.3" fill="#fff" fillOpacity="0.85" />
            <rect x="8.9" y="9" width="2.6" height="8" rx="1.3" fill="#fff" fillOpacity="0.92" />
            <rect x="12.8" y="6.2" width="2.6" height="10.8" rx="1.3" fill="#fff" />
            <circle cx="14.1" cy="4.1" r="1.7" fill="var(--color-amber)" />
          </svg>
          <p className="app__eyebrow">AI Career Coach</p>
        </div>
        <h1>Turn any job description into a 6-week plan.</h1>
        <p className="app__subhead">
          Paste a job description — or upload it as a PDF — and get a personalized roadmap:
          the skills that matter, a phased weekly schedule, learning resources, and mock
          interview milestones.
        </p>
      </header>

      <JdInput onResult={setResult} />

      {result ? (
        <section className="app__result">
          <div className="input-card__eyebrow app__result-eyebrow">
            <span className="step-badge">2</span>
            <span>Your roadmap</span>
          </div>

          {result.state?.partial_output && (
            <p className="app__partial-notice">
              <span className="app__partial-notice-dot" aria-hidden="true" />
              Roadmap generated with limited validation — a few checks didn't fully pass
              after retries. Worth a skim on the Agent Logs tab, but the plan below is safe
              to use.
            </p>
          )}

          <RoadmapTabs result={result} />

          <p className="app__session-id">Session {result.session_id}</p>
        </section>
      ) : (
        <section className="app__empty" aria-hidden="true">
          <p className="app__empty-title">Your roadmap will appear here</p>
          <p className="app__empty-body">
            Once you generate a roadmap, you'll see a week-by-week timeline, a skills
            breakdown, and curated resources for each stage.
          </p>
        </section>
      )}
    </div>
  );
}
