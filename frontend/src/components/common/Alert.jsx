export function Alert({
  text,
  onClose,
}) {
  return (
    <div className="alert error-alert">
      <span>
        {text}
      </span>

      <button
        onClick={onClose}
      >
        ×
      </button>
    </div>
  );
}


export function SuccessAlert({
  text,
  onClose,
}) {
  return (
    <div className="alert success-alert">
      <span>
        {text}
      </span>

      <button
        onClick={onClose}
      >
        ×
      </button>
    </div>
  );
}