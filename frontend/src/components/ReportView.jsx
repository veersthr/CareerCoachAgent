import { useEffect, useMemo, useRef, useState } from "react";
import { marked } from "marked";
import DOMPurify from "dompurify";
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
let mermaidRenderCounter = 0;

export default function ReportView({ markdown }) {
  const containerRef = useRef(null);
  const [renderError, setRenderError] = useState(null);

  const html = useMemo(() => {
    if (!markdown) return "";
    // report_markdown embeds LLM-generated text (skill names, resource topics,
    // interview questions) plus resource links — sanitize before injecting as HTML.
    return DOMPurify.sanitize(marked.parse(markdown), { ADD_ATTR: ["target"] });
  }, [markdown]);

  // marked renders ```mermaid fences as <pre><code class="language-mermaid">...</code></pre>.
  // Swap each one for an actual rendered chart after the sanitized HTML is in the DOM.
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    let cancelled = false;

    function openExternalLinksInNewTab() {
      container.querySelectorAll("a[href^='http']").forEach((a) => {
        a.setAttribute("target", "_blank");
        a.setAttribute("rel", "noopener noreferrer");
      });
    }

    async function renderMermaidBlocks() {
      setRenderError(null);
      openExternalLinksInNewTab();
      const blocks = Array.from(container.querySelectorAll("code.language-mermaid"));
      for (const block of blocks) {
        const pre = block.closest("pre");
        if (!pre) continue;
        const code = block.textContent;
        try {
          const id = `report-mermaid-${mermaidRenderCounter++}`;
          const { svg } = await mermaid.render(id, code);
          if (cancelled) return;
          const wrapper = document.createElement("div");
          wrapper.className = "gantt-chart";
          wrapper.innerHTML = svg;
          pre.replaceWith(wrapper);
        } catch (err) {
          if (!cancelled) {
            setRenderError(err.message || "Could not render an embedded diagram.");
          }
        }
      }
    }

    renderMermaidBlocks();
    return () => {
      cancelled = true;
    };
  }, [html]);

  if (!markdown) {
    return <p>No report available.</p>;
  }

  return (
    <div className="report-view">
      {renderError && <p className="gantt-chart__error">{renderError}</p>}
      <div ref={containerRef} dangerouslySetInnerHTML={{ __html: html }} />
    </div>
  );
}
