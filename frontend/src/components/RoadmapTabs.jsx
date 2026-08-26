import { useState } from "react";
import ReportView from "./ReportView";
import TimelineView from "./TimelineView";
import AgentLogs from "./AgentLogs";
import GanttChart from "./GanttChart";

const TABS = [
  { id: "timeline", label: "Timeline" },
  { id: "report", label: "Report" },
  { id: "gantt", label: "Gantt" },
  { id: "logs", label: "Agent logs" },
];

export default function RoadmapTabs({ result }) {
  const [activeTab, setActiveTab] = useState(TABS[0].id);
  const { report_markdown: reportMarkdown, state } = result;

  return (
    <div className="roadmap-tabs">
      <div className="roadmap-tabs__nav" role="tablist" aria-label="Roadmap sections">
        {TABS.map((tab, i) => (
          <button
            key={tab.id}
            role="tab"
            aria-selected={tab.id === activeTab}
            className={tab.id === activeTab ? "active" : ""}
            onClick={() => setActiveTab(tab.id)}
          >
            <span className="roadmap-tabs__num">{String(i + 1).padStart(2, "0")}</span>
            {tab.label}
          </button>
        ))}
      </div>

      <div className="roadmap-tabs__content">
        {activeTab === "timeline" && (
          <TimelineView weeklyPlan={state?.weekly_plan} resources={state?.resources} />
        )}
        {activeTab === "report" && <ReportView markdown={reportMarkdown} />}
        {activeTab === "gantt" && <GanttChart mermaidCode={state?.gantt_mermaid} />}
        {activeTab === "logs" && <AgentLogs logs={state?.agent_logs} />}
      </div>
    </div>
  );
}
