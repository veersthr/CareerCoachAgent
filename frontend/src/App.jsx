import { useState } from "react";
import JdInput from "./components/JdInput";
import RoadmapTabs from "./components/RoadmapTabs";
import "./App.css";

export default function App() {
  const [result, setResult] = useState(null);

  return (
    <div className="app">
      <header className="app__header">
        <p className="app__eyebrow">AI Career Coach</p>
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
