import { LockKeyhole, LogIn, User } from "lucide-react";
import { FormEvent, useState } from "react";

import { useAuth } from "../state/AuthContext";

export function LoginPage() {
  const { login } = useAuth();
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(username, password);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "No se pudo iniciar sesion");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="login-shell">
      <section className="login-panel">
        <div className="brand large">
          <div className="brand-mark">R</div>
          <div>
            <strong>REGIS Search</strong>
            <span>Acceso seguro</span>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="form-stack">
          <label>
            Usuario
            <div className="input-with-icon">
              <User size={18} />
              <input value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" />
            </div>
          </label>
          <label>
            Contrasena
            <div className="input-with-icon">
              <LockKeyhole size={18} />
              <input
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                type="password"
                autoComplete="current-password"
              />
            </div>
          </label>
          {error ? <p className="error-text">{error}</p> : null}
          <button className="primary-button" disabled={loading} type="submit">
            <LogIn size={18} />
            {loading ? "Entrando..." : "Entrar"}
          </button>
        </form>
      </section>
    </main>
  );
}
