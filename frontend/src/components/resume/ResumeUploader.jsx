import {
  useState,
} from "react";

import {
  apiRequest,
} from "../../api/api";


function ResumeUploader({
  onUploaded,
}) {
  const [file, setFile] =
    useState(null);

  const [loading, setLoading] =
    useState(false);

  const [
    statusText,
    setStatusText,
  ] = useState("");


  async function upload() {
    if (!file) {
      setStatusText(
        "Choose a PDF first.",
      );

      return;
    }

    try {
      setLoading(true);

      setStatusText("");

      const body =
        new FormData();

      body.append(
        "file",
        file,
      );

      await apiRequest(
        "/resumes",
        {
          method: "POST",
          body,
        },
      );

      setStatusText(
        "Resume processed successfully.",
      );

      setFile(null);

      await onUploaded();
    } catch (err) {
      setStatusText(
        err.message,
      );
    } finally {
      setLoading(false);
    }
  }


  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">
            PROFILE
          </span>

          <h3>
            Resume intelligence
          </h3>
        </div>
      </div>

      <div className="upload-box">
        <div className="upload-icon">
          ↑
        </div>

        <strong>
          Upload your resume
        </strong>

        <p>
          PDF up to 5 MB. NEXUS
          extracts your experience
          and creates a semantic
          embedding.
        </p>

        <input
          type="file"
          accept=".pdf,application/pdf"
          onChange={(event) =>
            setFile(
              event.target
                .files?.[0] ||
                null,
            )
          }
        />

        {file && (
          <span className="file-name">
            {file.name}
          </span>
        )}

        <button
          className="primary-button"
          onClick={upload}
          disabled={loading}
        >
          {loading
            ? "Processing..."
            : "Upload & analyse"}
        </button>

        {statusText && (
          <small>
            {statusText}
          </small>
        )}
      </div>
    </section>
  );
}


export default ResumeUploader;