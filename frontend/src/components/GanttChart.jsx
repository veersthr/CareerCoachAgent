import { useEffect, useRef, useState } from "react";
import mermaid from "mermaid";

mermaid.initialize({
  startOnLoad: false,
  theme: "base",
  themeVariables: {
    fontFamily: "Inter, -apple-system, sans-serif",
    primaryColor: "#e7efec",
    primaryBorderColor: "#1f5c4e",
    primaryTextColor: "#202a24",
    secondaryColor: "#f7ecd8",
    tertiaryColor: "#e8eef2",
    lineColor: "#c7cfc2",
    textColor: "#202a24",
    taskTextColor: "#202a24",
    taskTextOutsideColor: "#202a24",
    todayLineColor: "#c98a2b",
    sectionBkgColor: "#e7efec",
    sectionBkgColor2: "#f5f6f1",
    gridColor: "#dde3da",
  },
});

let renderCounter = 0;

export default function GanttChart({ mermaidCode }) {
  const containerRef = useRef(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function render() {
      setError(null);
      if (!mermaidCode || !mermaidCode.trim()) {
        return;
      }
      const id = `gantt-${renderCounter++}`;
      try {
        const { svg } = await mermaid.render(id, mermaidCode);
        if (!cancelled && containerRef.current) {
          containerRef.current.innerHTML = svg;
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message || "Could not render the Gantt chart.");
        }
      }
    }

    render();
    return () => {
      cancelled = true;
    };
  }, [mermaidCode]);

  if (!mermaidCode || !mermaidCode.trim()) {
    return <p>No Gantt chart available for this roadmap.</p>;
  }

  return (
    <div className="gantt-chart">
      {error && <p className="gantt-chart__error">{error}</p>}
      <div ref={containerRef} />
    </div>
  );
}
