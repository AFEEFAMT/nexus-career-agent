import StatCard from "../components/common/StatCard";
import ResumeUploader from "../components/resume/ResumeUploader";


function PipelineStep({
  number,
  title,
  text,
}) {
  return (
    <div className="pipeline-step">
      <span>
        {number}
      </span>

      <div>
        <strong>
          {title}
        </strong>

        <p>
          {text}
        </p>
      </div>
    </div>
  );
}


function OverviewPage({
  resumes,
  matches,
  shortlist,
  briefings,
  onResumeUploaded,
  onGoToMatches,
}) {
  const latestBriefing =
    briefings?.[0];


  return (
    <>
      <section className="hero-card">
        <div>
          <span className="hero-badge">
            YOUR AI CAREER AGENT
          </span>

          <h2>
            Discover opportunities
            that actually fit you.
          </h2>

          <p>
            NEXUS continuously
            transforms messy job
            listings into structured
            intelligence, matches them
            against your resume and
            helps you act on the best
            opportunities.
          </p>

          <div className="hero-actions">
            <button
              className="primary-button"
              onClick={
                onGoToMatches
              }
            >
              View matches
            </button>
          </div>
        </div>

        <div className="hero-graphic">
          <div className="ai-ring">
            AI
          </div>

          <div className="floating-chip chip-one">
            Semantic matching
          </div>

          <div className="floating-chip chip-two">
            Career agent
          </div>
        </div>
      </section>

      <section className="stats-grid">
        <StatCard
          title="Resume"
          value={
            resumes.length
              ? "Ready"
              : "Missing"
          }
          subtitle={
            resumes.length
              ? "Profile indexed"
              : "Upload your PDF"
          }
        />

        <StatCard
          title="Matches"
          value={matches.length}
          subtitle="Semantic matches"
        />

        <StatCard
          title="Shortlist"
          value={
            shortlist.length
          }
          subtitle="Saved opportunities"
        />

        <StatCard
          title="Briefing"
          value={
            latestBriefing
              ? latestBriefing.status
              : "None"
          }
          subtitle="Latest briefing"
        />
      </section>

      <div className="two-column">
        <ResumeUploader
          onUploaded={
            onResumeUploaded
          }
        />

        <section className="panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">
                PIPELINE
              </span>

              <h3>
                How NEXUS works
              </h3>
            </div>
          </div>

          <div className="pipeline-list">
            <PipelineStep
              number="01"
              title="Scrape"
              text="Collect opportunities from multiple public sources."
            />

            <PipelineStep
              number="02"
              title="Structure"
              text="Gemini converts raw listings into validated JSON."
            />

            <PipelineStep
              number="03"
              title="Match"
              text="pgvector ranks jobs using semantic similarity."
            />

            <PipelineStep
              number="04"
              title="Act"
              text="Agent, shortlist and briefing help you decide."
            />
          </div>
        </section>
      </div>
    </>
  );
}


export default OverviewPage;