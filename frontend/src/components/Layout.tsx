import { BriefcaseBusiness, LogOut, Search, UploadCloud } from "lucide-react";
import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";

import { useAuth } from "../state/AuthContext";

export function Layout({ children }: { children: ReactNode }) {
  const { logout, user } = useAuth();

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">R</div>
          <div>
            <strong>REGIS Search</strong>
            <span>Consulta operativa</span>
          </div>
        </div>

        <nav className="nav-list" aria-label="Navegacion principal">
          <NavLink to="/" end>
            <Search size={18} />
            Busquedas
          </NavLink>
          <NavLink to="/jobs">
            <UploadCloud size={18} />
            Jobs
          </NavLink>
        </nav>

        <div className="sidebar-footer">
          <div className="user-pill">
            <BriefcaseBusiness size={16} />
            <span>{user?.username || "usuario"}</span>
            <small>{user?.role || "rol"}</small>
          </div>
          <button className="icon-text-button muted" type="button" onClick={logout}>
            <LogOut size={17} />
            Salir
          </button>
        </div>
      </aside>

      <main className="content">{children}</main>
    </div>
  );
}
