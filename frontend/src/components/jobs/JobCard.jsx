import ScoreRing from "./ScoreRing";


function JobCard({
  match,
  saved,
  onSave,
}) {
  return (
    <article className="job-card">
      <div className="job-top">
        <div>
          <span className="source-badge">
            {match.source}
          </span>

          <h3>
            {match.title}
          </h3>

          <p className="company">
            {match.company ||
              "Company not extracted"}
          </p>
        </div>

        <ScoreRing
          score={match.score}
        />
      </div>


      <div className="job-meta">
        <span>
          {match.location ||
            "Location unavailable"}
        </span>

        {match.remote_ok ===
          true && (
          <span>
            Remote
          </span>
        )}

        {match.experience_level && (
          <span>
            {
              match.experience_level
            }
          </span>
        )}
      </div>


      {match.required_skills
        ?.length > 0 && (
        <div className="skills">
          {match.required_skills
            .slice(0, 5)
            .map((skill) => (
              <span key={skill}>
                {skill}
              </span>
            ))}
        </div>
      )}


      {match.is_search_result ? (
        <div className="reason-box">
          <span>
            SEMANTIC RELEVANCE
          </span>

          <p>
            This score is based on
            vector similarity between
            your search query and the
            job listing, rather than
            exact keyword matching.
          </p>
        </div>
      ) : (
        <div className="reason-box">
          <span>
            WHY IT MATCHES
          </span>

          <p>
            {match.justification ||
              "Generate AI explanations to see why this role aligns with your profile."}
          </p>
        </div>
      )}


      <div className="job-actions">
        <button
          className={
            saved
              ? "saved-button"
              : "secondary-button"
          }
          onClick={onSave}
          disabled={saved}
        >
          {saved
            ? "Saved ✓"
            : "Add to shortlist"}
        </button>

        {match.source_url && (
          <a
            href={
              match.source_url
            }
            target="_blank"
            rel="noreferrer"
            className="link-button"
          >
            View job ↗
          </a>
        )}
      </div>
    </article>
  );
}


export default JobCard;