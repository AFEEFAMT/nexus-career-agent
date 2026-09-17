import {
  useEffect,
  useState,
} from "react";

import {
  apiRequest,
  clearToken,
  getToken,
} from "./api/api";

import {
  Alert,
  SuccessAlert,
} from "./components/common/Alert";

import Loader from "./components/common/Loader";

import Header from "./components/layout/Header";
import Sidebar from "./components/layout/Sidebar";

import AgentPage from "./pages/AgentPage";
import AuthPage from "./pages/AuthPage";
import BriefingPage from "./pages/BriefingPage";
import MatchesPage from "./pages/MatchesPage";
import OverviewPage from "./pages/OverviewPage";
import ShortlistPage from "./pages/ShortlistPage";


function App() {
  const [
    tokenPresent,
    setTokenPresent,
  ] = useState(
    Boolean(getToken()),
  );

  const [user, setUser] =
    useState(null);

  const [
    activeTab,
    setActiveTab,
  ] = useState("Overview");

  const [loading, setLoading] =
    useState(false);

  const [message, setMessage] =
    useState("");

  const [error, setError] =
    useState("");

  const [resumes, setResumes] =
    useState([]);

  const [
    selectedResume,
    setSelectedResume,
  ] = useState(null);

  const [matches, setMatches] =
    useState([]);

  const [
    shortlist,
    setShortlist,
  ] = useState([]);

  const [
    briefings,
    setBriefings,
  ] = useState([]);


  useEffect(() => {
    if (!tokenPresent) {
      return;
    }

    initialize();
  }, [tokenPresent]);


  async function initialize() {
    try {
      setLoading(true);

      setError("");

      const [
        me,
        resumeData,
        shortlistData,
        briefingData,
      ] = await Promise.all([
        apiRequest("/auth/me"),

        apiRequest("/resumes"),

        apiRequest(
          "/shortlist",
        ),

        apiRequest(
          "/briefings",
        ),
      ]);

      setUser(me);

      setResumes(
        resumeData || [],
      );

      setShortlist(
        shortlistData || [],
      );

      setBriefings(
        briefingData || [],
      );

      if (resumeData?.length) {
        const latest =
          resumeData[0];

        setSelectedResume(
          latest,
        );

        try {
          const existingMatches =
            await apiRequest(
              `/matches/${latest.id}`,
            );

          setMatches(
            existingMatches ||
              [],
          );
        } catch {
          setMatches([]);
        }
      } else {
        setSelectedResume(
          null,
        );

        setMatches([]);
      }
    } catch (err) {
      if (!getToken()) {
        setTokenPresent(
          false,
        );
      }

      setError(
        err.message,
      );
    } finally {
      setLoading(false);
    }
  }


  async function refreshShortlist() {
    const data =
      await apiRequest(
        "/shortlist",
      );

    setShortlist(
      data || [],
    );

    return data || [];
  }


  async function refreshBriefings() {
    const data =
      await apiRequest(
        "/briefings",
      );

    setBriefings(
      data || [],
    );

    return data || [];
  }


  function logout() {
    clearToken();

    setTokenPresent(false);

    setUser(null);

    setResumes([]);

    setMatches([]);

    setShortlist([]);

    setBriefings([]);

    setSelectedResume(null);

    setActiveTab(
      "Overview",
    );
  }


  if (!tokenPresent) {
    return (
      <AuthPage
        onAuthenticated={() =>
          setTokenPresent(
            true,
          )
        }
      />
    );
  }


  return (
    <div className="app-shell">
      <Sidebar
        user={user}
        activeTab={activeTab}
        setActiveTab={
          setActiveTab
        }
        logout={logout}
      />

      <main className="main-content">
        <Header
          activeTab={
            activeTab
          }
        />

        {error && (
          <Alert
            text={error}
            onClose={() =>
              setError("")
            }
          />
        )}

        {message && (
          <SuccessAlert
            text={message}
            onClose={() =>
              setMessage("")
            }
          />
        )}

        {loading ? (
          <Loader />
        ) : (
          <>
            {activeTab ===
              "Overview" && (
              <OverviewPage
                resumes={
                  resumes
                }
                matches={
                  matches
                }
                shortlist={
                  shortlist
                }
                briefings={
                  briefings
                }
                onResumeUploaded={
                  initialize
                }
                onGoToMatches={() =>
                  setActiveTab(
                    "Matches",
                  )
                }
              />
            )}

            {activeTab ===
              "Matches" && (
              <MatchesPage
                resumes={
                  resumes
                }
                selectedResume={
                  selectedResume
                }
                setSelectedResume={
                  setSelectedResume
                }
                matches={
                  matches
                }
                setMatches={
                  setMatches
                }
                shortlist={
                  shortlist
                }
                refreshShortlist={
                  refreshShortlist
                }
                setError={
                  setError
                }
                setMessage={
                  setMessage
                }
              />
            )}

            {activeTab ===
              "Shortlist" && (
              <ShortlistPage
  shortlist={
    shortlist
  }
  briefings={
    briefings
  }
  refreshShortlist={
    refreshShortlist
  }
  setError={
    setError
  }
  setMessage={
    setMessage
  }
/>
            )}

            {activeTab ===
              "Agent" && (
              <AgentPage />
            )}

            {activeTab ===
              "Briefing" && (
              <BriefingPage
                briefings={
                  briefings
                }
                refreshBriefings={
                  refreshBriefings
                }
                setBriefings={
                  setBriefings
                }
              />
            )}
          </>
        )}
      </main>
    </div>
  );
}


export default App;
