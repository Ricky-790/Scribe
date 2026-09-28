import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { apiRequest, ApiError } from "../lib/api";
import { AuthLayout, FormError, FormField } from "../components/AuthLayout";

export const SignupPage: React.FC = () => {
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();

  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (isAuthenticated) navigate("/chat", { replace: true });
  }, [isAuthenticated, navigate]);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const data = await apiRequest("/auth/signup", {
        method: "POST",
        body: { username, email, password },
      });
      if (!data?.access_token) {
        throw new ApiError("Unexpected response from server.", 500);
      }
      login(data.access_token);
      navigate("/chat", { replace: true });
    } catch (err) {
      if (err instanceof ApiError) setError(err.message);
      else setError("Something went wrong. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthLayout
      title="Create your account"
      subtitle="Free while Scribe is in beta. Your first report takes a few minutes."
      footer={
        <p className="font-body-sm text-body-sm text-on-surface-variant">
          Already have an account?{" "}
          <Link
            to="/login"
            className="link-underline font-medium text-accent transition-colors hover:text-accent-fixed-dim"
          >
            Log in
          </Link>
        </p>
      }
    >
      <form onSubmit={onSubmit} className="flex flex-col gap-5">
        <FormField
          id="username"
          label="Username"
          type="text"
          value={username}
          onChange={setUsername}
          placeholder="ada"
          autoComplete="username"
        />
        <FormField
          id="email"
          label="Email"
          type="email"
          value={email}
          onChange={setEmail}
          placeholder="name@example.com"
          autoComplete="email"
        />
        <FormField
          id="password"
          label="Password"
          type="password"
          value={password}
          onChange={setPassword}
          placeholder="At least 6 characters"
          autoComplete="new-password"
          minLength={6}
        />

        <FormError message={error} />

        <button
          type="submit"
          disabled={submitting}
          className="btn btn-primary btn-sheen mt-1 w-full py-3.5"
        >
          {submitting ? (
            <>
              <span className="material-symbols-outlined animate-spin-slow text-[18px]">
                progress_activity
              </span>
              Creating account…
            </>
          ) : (
            <>
              Create account
              <span className="material-symbols-outlined text-[18px]">
                arrow_forward
              </span>
            </>
          )}
        </button>

        <p className="text-center font-body-sm text-[12px] leading-relaxed text-outline">
          By continuing you agree to let Scribe research things on your behalf.
        </p>
      </form>
    </AuthLayout>
  );
};
