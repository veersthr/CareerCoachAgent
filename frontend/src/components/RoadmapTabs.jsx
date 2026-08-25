import { useState } from "react";
import ReportView from "./ReportView";
import TimelineView from "./TimelineView";
import AgentLogs from "./AgentLogs";
import GanttChart from "./GanttChart";

const TABS = ["Report", "Timeline", "Agent Logs", "Gantt"];

export default function RoadmapTabs({ result }) {
  const [activeTab, setActiveTab] = useState(TABS[0]);
  const { report_markdown: reportMarkdown, state } = result;

  return (
    <div className="roadmap-tabs">
      <div className="roadmap-tabs__nav">
        {TABS.map((tab) => (
          <button
            key={tab}
            className={tab === activeTab ? "active" : ""}
            onClick={() => setActiveTab(tab)}
          >
            {tab}
          </button>
        ))}
      </div>

      <div className="roadmap-tabs__content">
        {activeTab === "Report" && <ReportView markdown={reportMarkdown} />}
        {activeTab === "Timeline" && (
          <TimelineView weeklyPlan={state?.weekly_plan} resources={state?.resources} />
        )}
        {activeTab === "Agent Logs" && <AgentLogs logs={state?.agent_logs} />}
        {activeTab === "Gantt" && <GanttChart mermaidCode={state?.gantt_mermaid} />}
      </div>
    </div>
  );
}
