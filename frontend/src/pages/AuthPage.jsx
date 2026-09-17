import {
  useState,
} from "react";

import {
  apiRequest,
  setToken,
} from "../api/api";


function AuthPage({
  onAuthenticated,
}) {
  const [mode, setMode] =
    useState("login");

  const [email, setEmail] =
    useState("");

  const [password, setPassword] =
    useState("");

  const [loading, setLoading] =
    useState(false);

  const [error, setError] =
    useState("");


  async function submit(event) {
    event.preventDefault();

    try {
      setLoading(true);

      setError("");

      const data =
        await apiRequest(
          mode === "login"
            ? "/auth/login"
            : "/auth/register",
          {
            method: "POST",

            body:
              JSON.stringify({
                email,
                password,
              }),
          },
        );

      if (data?.access_token) {
        setToken(
          data.access_token,
        );

        onAuthenticated();

        return;
      }

      if (
        mode === "register"
      ) {
        const loginData =
          await apiRequest(
            "/auth/login",
            {
              method: "POST",

              body:
                JSON.stringify({
                  email,
                  password,
                }),
            },
          );

        setToken(
          loginData.access_token,
        );

        onAuthenticated();
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }


  return (
    <div className="auth-page">
      <div className="auth-brand">
        <div className="logo-orb">
          N
        </div>

        <h1>
          NEXUS
        </h1>

        <p>
          Autonomous Career
          Intelligence
        </p>
      </div>

      <div className="auth-card">
        <div className="auth-heading">
          <span>
            {mode === "login"
              ? "Welcome back"
              : "Create your account"}
          </span>

          <h2>
            {mode === "login"
              ? "Sign in to NEXUS"
              : "Start your career intelligence workspace"}
          </h2>
        </div>

        {error && (
          <div className="inline-error">
            {error}
          </div>
        )}

        <form onSubmit={submit}>
          <label>
            Email
          </label>

          <input
            type="email"
            value={email}
            onChange={(event) =>
              setEmail(
                event.target.value,
              )
            }
            placeholder="you@example.com"
            required
          />

          <label>
            Password
          </label>

          <input
            type="password"
            value={password}
            onChange={(event) =>
              setPassword(
                event.target.value,
              )
            }
            placeholder="Minimum 8 characters"
            minLength={8}
            required
          />

          <button
            className="primary-button full-button"
            disabled={loading}
          >
            {loading
              ? "Please wait..."
              : mode === "login"
                ? "Sign in"
                : "Create account"}
          </button>
        </form>

        <button
          className="text-button"
          onClick={() => {
            setError("");

            setMode(
              mode === "login"
                ? "register"
                : "login",
            );
          }}
        >
          {mode === "login"
            ? "New here? Create an account"
            : "Already have an account? Sign in"}
        </button>
      </div>
    </div>
  );
}


export default AuthPage;