import { LogOut, Search, UploadCloud } from "lucide-react";
import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";

import { useAuth } from "../state/AuthContext";

function initials(value: string | undefined): string {
  if (!value) {
    return "U";
  }
  const parts = value.trim().split(/\s+/).slice(0, 2);
  return parts.map((part) => part[0]?.toUpperCase() || "").join("") || value[0].toUpperCase();
}

export function Layout({ children }: { children: ReactNode }) {
  const { logout, user } = useAuth();

  return (
    <div className="app-shell">
      <aside className="rail">
        <div className="rail-brand" title="REGIS Search">
          R
        </div>

        <nav className="rail-nav" aria-label="Navegacion principal">
          <NavLink className="rail-item" to="/" end>
            <Search size={20} />
            Buscar
          </NavLink>
          <NavLink className="rail-item" to="/jobs">
            <UploadCloud size={20} />
            Jobs
          </NavLink>
        </nav>

        <div className="rail-spacer" />
        <div className="rail-user" title={`${user?.username || "usuario"} (${user?.role || "rol"})`}>
          {initials(user?.username)}
        </div>
        <button className="rail-item" type="button" onClick={logout} title="Cerrar sesion">
          <LogOut size={20} />
          Salir
        </button>
      </aside>

      <main className="content">{children}</main>
    </div>
  );
}
