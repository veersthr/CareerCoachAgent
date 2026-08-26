const WEEK_META = {
  1: { phase: "Foundation", phaseClass: "phase-foundation" },
  2: { phase: "Foundation", phaseClass: "phase-foundation" },
  3: { phase: "Intermediate", phaseClass: "phase-intermediate" },
  4: { phase: "Intermediate", phaseClass: "phase-intermediate" },
  5: { phase: "Expert", phaseClass: "phase-expert" },
  6: { phase: "Expert", phaseClass: "phase-expert" },
};

export default function TimelineView({ weeklyPlan, resources }) {
  if (!weeklyPlan) {
    return <p className="timeline-view__empty">No weekly timeline available.</p>;
  }

  const resourcesBySkill = new Map((resources || []).map((r) => [r.skill, r]));

  return (
    <div className="roadmap-spine">
      {Object.keys(WEEK_META).map((weekStr, i) => {
        const week = Number(weekStr);
        const meta = WEEK_META[week];
        const skills = weeklyPlan[week] ?? weeklyPlan[weekStr] ?? [];
        return (
          <div
            className={`roadmap-spine__week ${meta.phaseClass}`}
            key={week}
            style={{ "--reveal-delay": `${i * 90}ms` }}
          >
            <div className="roadmap-spine__marker">
              <span className="roadmap-spine__number">{week}</span>
            </div>
            <div className="roadmap-spine__card">
              <div className="roadmap-spine__card-head">
                <h3>Week {week}</h3>
                <span className={`phase-tag ${meta.phaseClass}`}>{meta.phase}</span>
              </div>
              {skills.length === 0 ? (
                <p className="roadmap-spine__no-skills">No skills scheduled this week.</p>
              ) : (
                <ul className="roadmap-spine__skills">
                  {skills.map((skillName) => {
                    const resource = resourcesBySkill.get(skillName);
                    return (
                      <li key={skillName} className="roadmap-spine__skill">
                        <span className="roadmap-spine__skill-name">{skillName}</span>
                        {resource && (
                          <span className="roadmap-spine__resource">
                            <span className="resource-type-tag">{resource.resource_type}</span>
                            {resource.topic}
                          </span>
                        )}
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
