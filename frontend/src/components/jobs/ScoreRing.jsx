function ScoreRing({
  score,
}) {
  const rounded =
    Math.round(score || 0);

  return (
    <div
      className="score-ring"
      style={{
        "--score":
          `${rounded * 3.6}deg`,
      }}
    >
      <div>
        <strong>
          {rounded}
        </strong>

        <span>
          %
        </span>
      </div>
    </div>
  );
}


export default ScoreRing;