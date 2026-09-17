function Header({
  activeTab,
}) {
  return (
    <header className="page-header">
      <div>
        <span className="eyebrow">
          AI CAREER WORKSPACE
        </span>

        <h1>
          {activeTab}
        </h1>
      </div>

      <div className="status-pill">
        <span className="status-dot" />
        Nexus online
      </div>
    </header>
  );
}


export default Header;