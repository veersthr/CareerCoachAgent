import { useState } from "react";
import JdInput from "./components/JdInput";
import RoadmapTabs from "./components/RoadmapTabs";
import "./App.css";

export default function App() {
  const [result, setResult] = useState(null);

  return (
    <div className="app">
      <header className="app__header">
        <h1>AI Career Coach</h1>
        <p>Paste a job description (or upload one as a PDF) to get a 6-week learning roadmap.</p>
      </header>

      <JdInput onResult={setResult} />

      {result && (
        <section className="app__result">
          <p className="app__session-id">Session: {result.session_id}</p>
          {result.state?.partial_output && (
            <p className="app__partial-warning">
              This roadmap was generated with partial validation — some checks didn't pass
              after retries. See the Agent Logs tab for details.
            </p>
          )}
          <RoadmapTabs result={result} />
        </section>
      )}
    </div>
  );
}
