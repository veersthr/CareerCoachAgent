import { useEffect, useRef, useState } from "react";
import mermaid from "mermaid";

mermaid.initialize({ startOnLoad: false, theme: "default" });

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
