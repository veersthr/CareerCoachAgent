import { useMemo } from "react";
import { marked } from "marked";
import DOMPurify from "dompurify";

export default function ReportView({ markdown }) {
  const html = useMemo(() => {
    if (!markdown) return "";
    // report_markdown embeds LLM-generated text (skill names, resource topics,
    // interview questions) — sanitize before injecting as HTML.
    return DOMPurify.sanitize(marked.parse(markdown));
  }, [markdown]);

  if (!markdown) {
    return <p>No report available.</p>;
  }

  return <div className="report-view" dangerouslySetInnerHTML={{ __html: html }} />;
}
