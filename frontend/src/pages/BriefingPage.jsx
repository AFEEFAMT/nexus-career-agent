import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

import {
  apiRequest,
  mediaUrl,
} from "../api/api";

import StatusBadge from "../components/common/StatusBadge";


const ACTIVE_STATUSES = new Set([
  "queued",
  "processing",
]);


function BriefingPage({
  briefings,
  refreshBriefings,
  setBriefings,
}) {
  const [loading, setLoading] =
    useState(false);

  const [error, setError] =
    useState("");

  const pollingRef =
    useRef(false);

  const latest =
    briefings?.[0] || null;

  const latestId =
    latest?.id || null;

  const latestStatus =
    latest?.status || null;


  const pollBriefing = useCallback(
    async (briefingId) => {
      if (pollingRef.current) {
        return;
      }

      pollingRef.current = true;
      setLoading(true);

      try {
        // Poll for up to 5 minutes.
        for (
          let attempt = 0;
          attempt < 60;
          attempt += 1
        ) {
          const data =
            await apiRequest(
              `/briefings/${briefingId}`,
            );

          await refreshBriefings();

          if (
            data.status === "done"
            || data.status === "failed"
          ) {
            return;
          }

          await new Promise(
            (resolve) =>
              setTimeout(
                resolve,
                5000,
              ),
          );
        }
      } catch (err) {
        setError(err.message);
      } finally {
        pollingRef.current = false;
        setLoading(false);

        try {
          await refreshBriefings();
        } catch {
          // The next normal page refresh
          // will fetch the latest state.
        }
      }
    },
    [refreshBriefings],
  );


  useEffect(() => {
    if (
      latestId
      && ACTIVE_STATUSES.has(
        latestStatus,
      )
      && !pollingRef.current
    ) {
      void pollBriefing(
        latestId,
      );
    }
  }, [
    latestId,
    latestStatus,
    pollBriefing,
  ]);


  async function generate() {
    try {
      setLoading(true);
      setError("");

      const briefing =
        await apiRequest(
          "/briefings/generate",
          {
            method: "POST",
          },
        );

      setBriefings(
        (current) => [
          briefing,
          ...current,
        ],
      );

      await pollBriefing(
        briefing.id,
      );
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  }


  async function refreshOne(
    briefingId,
  ) {
    try {
      setError("");

      await apiRequest(
        `/briefings/${briefingId}`,
      );

      await refreshBriefings();
    } catch (err) {
      setError(err.message);
    }
  }


  return (
    <>
      <section className="briefing-hero">
        <div>
          <span className="hero-badge">
            WEEKLY INTELLIGENCE
          </span>

          <h2>
            Generate My Briefing
          </h2>

          <p>
            Nexus turns your top three
            semantic matches into a
            concise 60–90 second career
            briefing.
          </p>

          <button
            className="primary-button"
            onClick={generate}
            disabled={
              loading
              || ACTIVE_STATUSES.has(
                latestStatus,
              )
            }
          >
            {ACTIVE_STATUSES.has(
              latestStatus,
            )
              ? "Video is generating..."
              : loading
                ? "Generating..."
                : "Generate My Briefing"}
          </button>

          {error && (
            <div className="inline-error">
              {error}
            </div>
          )}
        </div>

        <div className="briefing-wave">
          <span />
          <span />
          <span />
          <span />
          <span />
          <span />
          <span />
        </div>
      </section>


      {latest && (
        <section className="panel latest-briefing">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">
                LATEST
              </span>

              <h3>
                Career briefing
              </h3>
            </div>

            <StatusBadge
              status={latest.status}
            />
          </div>


          <div className="briefing-meta">
            <span>
              Provider:{" "}
              <strong>
                {latest.provider
                  || "Waiting"}
              </strong>
            </span>

            <span>
              Format:{" "}
              <strong>
                {
                  latest.briefing_type
                }
              </strong>
            </span>
          </div>


          {ACTIVE_STATUSES.has(
            latest.status,
          ) && (
            <div
              className="reason-box"
              style={{
                marginTop: "18px",
              }}
            >
              <span>
                VIDEO GENERATION
              </span>

              <p>
                Tavus accepted the
                briefing and is rendering
                the avatar video. Nexus is
                polling the asynchronous
                job automatically.
              </p>

              <button
                className="secondary-button"
                style={{
                  marginTop: "10px",
                }}
                onClick={() =>
                  refreshOne(
                    latest.id,
                  )
                }
              >
                Refresh status
              </button>
            </div>
          )}


          {latest.script && (
            <div className="script-box">
              <span>
                SCRIPT
              </span>

              <p>
                {latest.script}
              </p>
            </div>
          )}


          {latest.media_url
            && latest.briefing_type
              === "audio" && (
              <audio
                controls
                className="audio-player"
                src={mediaUrl(
                  latest.media_url,
                )}
              />
            )}


          {latest.media_url
            && latest.briefing_type
              === "video" && (
              <video
                controls
                className="video-player"
                src={mediaUrl(
                  latest.media_url,
                )}
              />
            )}


          {latest.error_message && (
            <small className="muted">
              {
                latest.error_message
              }
            </small>
          )}
        </section>
      )}


      {briefings.length > 1 && (
        <section className="panel">
          <div className="panel-heading">
            <h3>
              Past briefings
            </h3>
          </div>

          <div className="history-list">
            {briefings
              .slice(1)
              .map(
                (briefing) => (
                  <div
                    className="history-row"
                    key={briefing.id}
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
                    </div>

                    <div
                      style={{
                        display: "flex",
                        gap: "10px",
                        alignItems:
                          "center",
                      }}
                    >
                      <StatusBadge
                        status={
                          briefing.status
                        }
                      />

                      {briefing.media_url
                        && briefing.status
                          === "done" && (
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
        </section>
      )}
    </>
  );
}


export default BriefingPage;