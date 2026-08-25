export default function AgentLogs({ logs }) {
  if (!logs || logs.length === 0) {
    return <p>No agent log entries for this run.</p>;
  }

  return (
    <ol className="agent-logs">
      {logs.map((line, i) => (
        <li key={i}>{line}</li>
      ))}
    </ol>
  );
}
