const PHASE_BY_WEEK = {
  1: "Foundation",
  2: "Foundation",
  3: "Intermediate",
  4: "Intermediate",
  5: "Expert",
  6: "Expert",
};

export default function TimelineView({ weeklyPlan, resources }) {
  if (!weeklyPlan) {
    return <p>No weekly timeline available.</p>;
  }

  const resourcesBySkill = new Map((resources || []).map((r) => [r.skill, r]));

  return (
    <div className="timeline-view">
      {Object.keys(PHASE_BY_WEEK).map((weekStr) => {
        const week = Number(weekStr);
        const skills = weeklyPlan[week] ?? weeklyPlan[weekStr] ?? [];
        return (
          <div className="timeline-view__week" key={week}>
            <h3>
              Week {week} <span className="timeline-view__phase">({PHASE_BY_WEEK[week]})</span>
            </h3>
            {skills.length === 0 ? (
              <p className="timeline-view__empty">No skills scheduled.</p>
            ) : (
              <ul>
                {skills.map((skillName) => {
                  const resource = resourcesBySkill.get(skillName);
                  return (
                    <li key={skillName}>
                      <strong>{skillName}</strong>
                      {resource && (
                        <span className="timeline-view__resource">
                          {" "}
                          — {resource.resource_type}: {resource.topic}
                        </span>
                      )}
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        );
      })}
    </div>
  );
}
