import {
  useMemo,
  useState,
} from "react";

import {
  apiRequest,
} from "../api/api";

import EmptyState from "../components/common/EmptyState";
import JobCard from "../components/jobs/JobCard";


function MatchesPage({
  resumes,
  selectedResume,
  setSelectedResume,
  matches,
  setMatches,
  shortlist,
  refreshShortlist,
  setError,
  setMessage,
}) {
  const [loading, setLoading] =
    useState(false);

  const [
    searchQuery,
    setSearchQuery,
  ] = useState("");

  const [
    searchResults,
    setSearchResults,
  ] = useState([]);

  const [
    searchMode,
    setSearchMode,
  ] = useState(false);

  const [
    searching,
    setSearching,
  ] = useState(false);


  const savedIds =
    useMemo(
      () =>
        new Set(
          shortlist.map(
            (item) =>
              item.job_id,
          ),
        ),
      [shortlist],
    );


  async function loadMatches(
    resumeId,
  ) {
    const data =
      await apiRequest(
        `/matches/${resumeId}`,
      );

    setMatches(
      data || [],
    );

    return data || [];
  }


  async function changeResume(
    resumeId,
  ) {
    const chosen =
      resumes.find(
        (resume) =>
          resume.id ===
          resumeId,
      );

    setSelectedResume(
      chosen || null,
    );

    setSearchMode(false);
    setSearchResults([]);

    if (!chosen) {
      setMatches([]);
      return;
    }

    try {
      setLoading(true);
      setError("");

      await loadMatches(
        chosen.id,
      );
    } catch (err) {
      setMatches([]);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }


  async function generateMatches() {
    if (!selectedResume) {
      setError(
        "Upload a resume first.",
      );

      return;
    }

    try {
      setLoading(true);
      setError("");

      setSearchMode(false);
      setSearchResults([]);

      const data =
        await apiRequest(
          `/matches/${selectedResume.id}/generate?limit=10`,
          {
            method: "POST",
          },
        );

      setMatches(
        data.matches || [],
      );

      setMessage(
        "Semantic resume matches generated.",
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }


  async function generateJustifications() {
    if (!selectedResume) {
      return;
    }

    try {
      setLoading(true);
      setError("");

      setSearchMode(false);

      const data =
        await apiRequest(
          `/matches/${selectedResume.id}/justify`,
          {
            method: "POST",
          },
        );

      setMatches(
        data || [],
      );

      setMessage(
        "AI explanations generated.",
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }


  async function refreshMetadata() {
    if (!selectedResume) {
      setError(
        "Upload a resume first.",
      );

      return;
    }

    try {
      setLoading(true);
      setError("");

      setSearchMode(false);

      const result =
        await apiRequest(
          "/jobs/enrich-matches?limit=10",
          {
            method: "POST",
          },
        );

      await loadMatches(
        selectedResume.id,
      );

      await refreshShortlist();

      if (result.rate_limited) {
        setMessage(
          `Updated ${result.enriched} job(s). Gemini quota was reached, so the remaining jobs can be refreshed later.`,
        );

        return;
      }

      if (
        result.errors?.length
      ) {
        setMessage(
          `Updated ${result.enriched} job(s). Some listings could not be extracted.`,
        );

        return;
      }

      setMessage(
        `Job details refreshed. ${result.enriched} updated, ${result.skipped} already complete.`,
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }


  async function runSemanticSearch(
    event,
  ) {
    event.preventDefault();

    const query =
      searchQuery.trim();

    if (!query) {
      setError(
        "Enter something to search for.",
      );

      return;
    }

    try {
      setSearching(true);
      setError("");

      const data =
        await apiRequest(
          `/jobs/search?q=${encodeURIComponent(query)}&limit=10`,
        );

      const normalized =
        (data || []).map(
          (job) => ({
            ...job,
            score:
              job.semantic_score,
            is_search_result:
              true,
          }),
        );

      setSearchResults(
        normalized,
      );

      setSearchMode(true);
    } catch (err) {
      setSearchResults([]);
      setError(err.message);
    } finally {
      setSearching(false);
    }
  }


  function clearSearch() {
    setSearchQuery("");
    setSearchResults([]);
    setSearchMode(false);
  }


  async function addShortlist(
    jobId,
  ) {
    try {
      await apiRequest(
        `/shortlist/${jobId}`,
        {
          method: "POST",
        },
      );

      await refreshShortlist();

      setMessage(
        "Job added to shortlist.",
      );
    } catch (err) {
      setError(err.message);
    }
  }


  const displayedJobs =
    searchMode
      ? searchResults
      : matches;


  return (
    <>
      <section className="toolbar-panel">
        <div>
          <span className="eyebrow">
            SEMANTIC SEARCH
          </span>

          <h3>
            Find opportunities by meaning
          </h3>

          <p>
            Search concepts such as
            "backend infra" even when
            listings use different
            terminology.
          </p>
        </div>

        <form
          className="semantic-search"
          onSubmit={
            runSemanticSearch
          }
        >
          <input
            type="text"
            value={searchQuery}
            onChange={(event) =>
              setSearchQuery(
                event.target.value,
              )
            }
            placeholder="Try: backend infra"
          />

          <button
            className="primary-button"
            disabled={searching}
          >
            {searching
              ? "Searching..."
              : "Semantic search"}
          </button>

          {searchMode && (
            <button
              type="button"
              className="secondary-button"
              onClick={clearSearch}
            >
              Clear
            </button>
          )}
        </form>
      </section>


      <section className="toolbar-panel">
        <div>
          <span className="eyebrow">
            RESUME MATCHING
          </span>

          <h3>
            Your best-fit jobs
          </h3>

          <p>
            Scores represent semantic
            similarity, not hiring
            probability.
          </p>
        </div>

        <div className="toolbar-actions">
          <select
            value={
              selectedResume?.id ||
              ""
            }
            onChange={(event) =>
              changeResume(
                event.target.value,
              )
            }
          >
            {resumes.map(
              (resume) => (
                <option
                  key={resume.id}
                  value={resume.id}
                >
                  {
                    resume.filename
                  }
                </option>
              ),
            )}
          </select>

          <button
            className="secondary-button"
            onClick={
              generateMatches
            }
            disabled={loading}
          >
            Generate matches
          </button>

          <button
            className="secondary-button"
            onClick={
              refreshMetadata
            }
            disabled={
              loading ||
              !matches.length
            }
          >
            {loading
              ? "Working..."
              : "Refresh job details"}
          </button>

          <button
            className="primary-button"
            onClick={
              generateJustifications
            }
            disabled={
              loading ||
              !matches.length
            }
          >
            Explain with AI
          </button>
        </div>
      </section>


      {searchMode && (
        <div className="search-context">
          <span>
            Semantic results for
          </span>

          <strong>
            “{searchQuery}”
          </strong>

          <small>
            {searchResults.length}
            {" "}
            results
          </small>
        </div>
      )}


      {!displayedJobs.length ? (
        <EmptyState
          title={
            searchMode
              ? "No semantic results"
              : "No matches yet"
          }
          text={
            searchMode
              ? "Try a broader career concept or skill."
              : "Generate semantic matches from your resume."
          }
        />
      ) : (
        <section className="job-grid">
          {displayedJobs.map(
            (job) => (
              <JobCard
                key={
                  job.match_id ||
                  job.job_id
                }
                match={job}
                saved={
                  savedIds.has(
                    job.job_id,
                  )
                }
                onSave={() =>
                  addShortlist(
                    job.job_id,
                  )
                }
              />
            ),
          )}
        </section>
      )}
    </>
  );
}


export default MatchesPage;