import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { ApiError } from "../api/client";

export function SignupClinicPage() {
  const { signupClinic } = useAuth();
  const navigate = useNavigate();
  const [clinicName, setClinicName] = useState("");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await signupClinic({
        clinic_name: clinicName,
        admin_email: email,
        admin_password: password,
        admin_full_name: fullName,
      });
      navigate("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Signup failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="page" style={{ maxWidth: 420, marginTop: 60 }}>
      <div className="card stack">
        <h1 style={{ fontSize: 20, margin: 0 }}>Set up your practice</h1>
        <p style={{ fontSize: 13, color: "var(--color-text-muted)", marginTop: 0 }}>
          Creates your clinic and a Super Admin account. You can add providers and assistants
          afterward.
        </p>
        <form className="stack" onSubmit={handleSubmit}>
          <input
            className="input"
            placeholder="Clinic / practice name"
            value={clinicName}
            onChange={(e) => setClinicName(e.target.value)}
            required
          />
          <input
            className="input"
            placeholder="Your full name"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            required
          />
          <input
            className="input"
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <input
            className="input"
            type="password"
            placeholder="Password (min 8 characters)"
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          {error && <div className="error-text">{error}</div>}
          <button className="btn btn-primary" type="submit" disabled={submitting}>
            {submitting ? "Creating…" : "Create clinic"}
          </button>
        </form>
        <div style={{ fontSize: 13 }}>
          Already have an account? <Link to="/login">Sign in</Link>
        </div>
      </div>
    </div>
  );
}
