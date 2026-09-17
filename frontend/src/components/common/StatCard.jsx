function StatCard({
  title,
  value,
  subtitle,
}) {
  return (
    <div className="stat-card">
      <span>
        {title}
      </span>

      <strong>
        {value}
      </strong>

      <small>
        {subtitle}
      </small>
    </div>
  );
}


export default StatCard;