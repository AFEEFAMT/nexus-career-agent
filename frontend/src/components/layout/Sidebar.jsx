const tabs = [
  "Overview",
  "Matches",
  "Shortlist",
  "Agent",
  "Briefing",
];


function tabIcon(tab) {
  const icons = {
    Overview: "⌂",
    Matches: "◎",
    Shortlist: "☆",
    Agent: "✦",
    Briefing: "▶",
  };

  return icons[tab];
}


function Sidebar({
  user,
  activeTab,
  setActiveTab,
  logout,
}) {
  return (
    <aside className="sidebar">
      <div>
        <div className="sidebar-brand">
          <div className="mini-logo">
            N
          </div>

          <div>
            <strong>
              NEXUS
            </strong>

            <span>
              Career Intelligence
            </span>
          </div>
        </div>

        <nav>
          {tabs.map((tab) => (
            <button
              key={tab}
              className={
                activeTab === tab
                  ? "nav-item active"
                  : "nav-item"
              }
              onClick={() =>
                setActiveTab(tab)
              }
            >
              <span>
                {tabIcon(tab)}
              </span>

              {tab}
            </button>
          ))}
        </nav>
      </div>

      <div className="sidebar-footer">
        <div className="sidebar-user">
          <div className="avatar">
            {user?.email
              ?.charAt(0)
              .toUpperCase() ||
              "U"}
          </div>

          <div>
            <span>
              Signed in
            </span>

            <strong>
              {user?.email ||
                "User"}
            </strong>
          </div>
        </div>

        <button
          className="logout-button"
          onClick={logout}
        >
          Sign out
        </button>
      </div>
    </aside>
  );
}


export default Sidebar;