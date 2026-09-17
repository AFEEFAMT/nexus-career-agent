import {
  useState,
} from "react";

import {
  apiRequest,
} from "../api/api";


function AgentPage() {
  const [input, setInput] =
    useState("");

  const [
    messages,
    setMessages,
  ] = useState([
    {
      role: "assistant",

      text:
        "Hi, I’m Nexus. Ask me about your best matches, saved jobs or opportunities in the database.",
    },
  ]);

  const [loading, setLoading] =
    useState(false);


  async function sendMessage(
    event,
  ) {
    event.preventDefault();

    const question =
      input.trim();

    if (!question) {
      return;
    }

    setMessages(
      (current) => [
        ...current,

        {
          role: "user",
          text: question,
        },
      ],
    );

    setInput("");

    setLoading(true);

    try {
      const data =
        await apiRequest(
          "/agent/chat",
          {
            method: "POST",

            body:
              JSON.stringify({
                message:
                  question,
              }),
          },
        );

      setMessages(
        (current) => [
          ...current,

          {
            role: "assistant",
            text: data.answer,
            tools:
              data.tools_used,
          },
        ],
      );
    } catch (err) {
      setMessages(
        (current) => [
          ...current,

          {
            role: "assistant",

            text:
              err.message.includes(
                "temporarily unavailable",
              )
                ? "Gemini is temporarily busy. Your database tools are ready; try again shortly."
                : err.message,

            error: true,
          },
        ],
      );
    } finally {
      setLoading(false);
    }
  }


  return (
    <section className="agent-layout">
      <div className="agent-info">
        <span className="hero-badge">
          TOOL-CALLING AGENT
        </span>

        <h2>
          Ask Nexus about
          your career data.
        </h2>

        <p>
          Nexus cannot directly
          access your database.
          Gemini chooses controlled
          backend tools which run
          securely using your
          authenticated user ID.
        </p>

        <div className="tool-list">
          <code>
            get_top_matches()
          </code>

          <code>
            search_jobs()
          </code>

          <code>
            get_shortlist()
          </code>

          <code>
            get_job_details()
          </code>
        </div>
      </div>

      <div className="chat-card">
        <div className="chat-header">
          <div>
            <strong>
              Nexus Agent
            </strong>

            <span>
              Grounded in saved data
            </span>
          </div>

          <span className="status-dot" />
        </div>

        <div className="chat-messages">
          {messages.map(
            (item, index) => (
              <div
                key={index}
                className={
                  item.role ===
                  "user"
                    ? "chat-row user-row"
                    : "chat-row"
                }
              >
                <div
                  className={
                    item.role ===
                    "user"
                      ? "chat-bubble user-bubble"
                      : "chat-bubble agent-bubble"
                  }
                >
                  <p>
                    {item.text}
                  </p>

                  {item.tools
                    ?.length > 0 && (
                    <div className="tool-used">
                      Tools:{" "}
                      {item.tools.join(
                        ", ",
                      )}
                    </div>
                  )}
                </div>
              </div>
            ),
          )}

          {loading && (
            <div className="chat-row">
              <div className="chat-bubble agent-bubble">
                <span className="typing">
                  Nexus is thinking...
                </span>
              </div>
            </div>
          )}
        </div>

        <form
          className="chat-input"
          onSubmit={
            sendMessage
          }
        >
          <input
            value={input}
            onChange={(event) =>
              setInput(
                event.target.value,
              )
            }
            placeholder="Ask about your matches..."
          />

          <button
            className="primary-button"
            disabled={loading}
          >
            Send
          </button>
        </form>
      </div>
    </section>
  );
}


export default AgentPage;