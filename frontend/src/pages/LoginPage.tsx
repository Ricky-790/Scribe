import React, { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { apiRequest, ApiError } from "../lib/api";
import { AuthLayout, FormError, FormField } from "../components/AuthLayout";

export const LoginPage: React.FC = () => {
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation() as { state?: { from?: string } };

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (isAuthenticated) {
      const dest = location.state?.from || "/chat";
      navigate(dest, { replace: true });
    }
  }, [isAuthenticated, navigate, location.state]);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const data: { access_token: string; token_type: string } =
        await apiRequest("/auth/signin", {
          method: "POST",
          body: { email, password },
        });
      if (!data?.access_token) {
        throw new ApiError("Unexpected response from server.", 500);
      }
      login(data.access_token);
      const dest = location.state?.from || "/chat";
      navigate(dest, { replace: true });
    } catch (err) {
      if (err instanceof ApiError) setError(err.message);
      else setError("Something went wrong. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthLayout
      title="Welcome back"
      subtitle="Pick up where your last report left off."
      footer={
        <p className="font-body-sm text-body-sm text-on-surface-variant">
          Don’t have an account?{" "}
          <Link
            to="/signup"
            className="link-underline font-medium text-accent transition-colors hover:text-accent-fixed-dim"
          >
            Sign up
          </Link>
        </p>
      }
    >
      <form onSubmit={onSubmit} className="flex flex-col gap-5">
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
          placeholder="••••••••"
          autoComplete="current-password"
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
              Signing in…
            </>
          ) : (
            <>
              Sign in
              <span className="material-symbols-outlined text-[18px]">
                arrow_forward
              </span>
            </>
          )}
        </button>
      </form>
    </AuthLayout>
  );
};
