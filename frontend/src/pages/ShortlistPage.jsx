import {
  apiRequest,
  mediaUrl,
} from "../api/api";

import EmptyState from "../components/common/EmptyState";
import ScoreRing from "../components/jobs/ScoreRing";
import StatusBadge from "../components/common/StatusBadge";


function ShortlistPage({
  shortlist,
  briefings,
  refreshShortlist,
  setError,
  setMessage,
}) {
  async function remove(
    jobId,
  ) {
    try {
      await apiRequest(
        `/shortlist/${jobId}`,
        {
          method: "DELETE",
        },
      );

      await refreshShortlist();

      setMessage(
        "Removed from shortlist.",
      );
    } catch (err) {
      setError(
        err.message,
      );
    }
  }


  return (
    <>
      <section className="toolbar-panel">
        <div>
          <span className="eyebrow">
            SAVED OPPORTUNITIES
          </span>

          <h3>
            My Shortlist
          </h3>

          <p>
            Your saved jobs with
            semantic match scores and
            briefing history.
          </p>
        </div>
      </section>


      {!shortlist.length ? (
        <EmptyState
          title="Your shortlist is empty"
          text="Save promising jobs from the Matches page."
        />
      ) : (
        <section className="job-grid">
          {shortlist.map(
            (item) => (
              <article
                className="job-card"
                key={
                  item.shortlist_id
                }
              >
                <div className="job-top">
                  <div>
                    <span className="source-badge">
                      {
                        item.source
                      }
                    </span>

                    <h3>
                      {
                        item.title
                      }
                    </h3>

                    <p className="company">
                      {item.company ||
                        "Company not extracted"}
                    </p>
                  </div>

                  {item.match_score !==
                    null &&
                    item.match_score !==
                      undefined && (
                      <ScoreRing
                        score={
                          item.match_score
                        }
                      />
                    )}
                </div>


                <div className="job-meta">
                  <span>
                    {item.location ||
                      "Location unavailable"}
                  </span>

                  {item.remote_ok ===
                    true && (
                    <span>
                      Remote
                    </span>
                  )}
                </div>


                {item.required_skills
                  ?.length > 0 && (
                  <div className="skills">
                    {item.required_skills
                      .slice(0, 5)
                      .map(
                        (skill) => (
                          <span
                            key={
                              skill
                            }
                          >
                            {
                              skill
                            }
                          </span>
                        ),
                      )}
                  </div>
                )}


                <div className="reason-box">
                  <span>
                    MATCH SCORE
                  </span>

                  <p>
                    {item.match_score !==
                    null &&
                    item.match_score !==
                      undefined
                      ? `${item.match_score}% semantic similarity with your latest resume.`
                      : "No match score is available for this job and your latest resume yet."}
                  </p>
                </div>


                <div className="job-actions">
                  <button
                    className="danger-button"
                    onClick={() =>
                      remove(
                        item.job_id,
                      )
                    }
                  >
                    Remove
                  </button>

                  {item.source_url && (
                    <a
                      href={
                        item.source_url
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
            ),
          )}
        </section>
      )}


      <section
        className="panel"
        style={{
          marginTop: "22px",
        }}
      >
        <div className="panel-heading">
          <div>
            <span className="eyebrow">
              HISTORY
            </span>

            <h3>
              Past Briefings
            </h3>
          </div>
        </div>

        {!briefings?.length ? (
          <p className="muted">
            You have not generated
            any briefings yet.
          </p>
        ) : (
          <div className="history-list">
            {briefings.map(
              (briefing) => (
                <div
                  className="history-row"
                  key={
                    briefing.id
                  }
                >
                  <div>
                    <strong>
                      Career briefing
                    </strong>

                    <span>
                      {new Date(
                        briefing.created_at,
                      ).toLocaleString()}
                    </span>

                    <div
                      style={{
                        marginTop:
                          "6px",
                      }}
                    >
                      <small>
                        {
                          briefing.provider ||
                          "Waiting"
                        }
                        {" • "}
                        {
                          briefing.briefing_type
                        }
                      </small>
                    </div>
                  </div>

                  <div
                    style={{
                      display:
                        "flex",
                      alignItems:
                        "center",
                      gap: "10px",
                    }}
                  >
                    <StatusBadge
                      status={
                        briefing.status
                      }
                    />

                    {briefing.media_url &&
                      briefing.status ===
                        "done" && (
                        <a
                          href={mediaUrl(
                            briefing.media_url,
                          )}
                          target="_blank"
                          rel="noreferrer"
                          className="link-button"
                        >
                          Open
                        </a>
                      )}
                  </div>
                </div>
              ),
            )}
          </div>
        )}
      </section>
    </>
  );
}


export default ShortlistPage;