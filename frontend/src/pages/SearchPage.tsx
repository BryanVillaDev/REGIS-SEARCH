import { useMutation, useQuery } from "@tanstack/react-query";
import { ChevronRight, FileUp, ListChecks, MapPin, Search, UserSearch } from "lucide-react";
import { FormEvent, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { createCedulasJob, createNombresJob, NameSearchParams, searchName } from "../api/client";

type SearchMode = "prefix" | "exact";
type SearchTab = "cedula" | "nombre" | "lote";
type LoteMode = "cedulas" | "nombres";

function nameInitials(value: string): string {
  const parts = value.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) {
    return "?";
  }
  const first = parts[0][0] || "";
  const last = parts.length > 1 ? parts[parts.length - 1][0] || "" : "";
  return (first + last).toUpperCase();
}

export function SearchPage() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<SearchTab>("cedula");
  const [loteMode, setLoteMode] = useState<LoteMode>("cedulas");
  const [cedula, setCedula] = useState("");
  const [apellido1, setApellido1] = useState("");
  const [apellido2, setApellido2] = useState("");
  const [nombre1, setNombre1] = useState("");
  const [nombre2, setNombre2] = useState("");
  const [mode, setMode] = useState<SearchMode>("prefix");
  const [offset, setOffset] = useState(0);
  const [submittedParams, setSubmittedParams] = useState<NameSearchParams | null>(null);
  const [cedulasText, setCedulasText] = useState("");
  const [nombresText, setNombresText] = useState("");

  const params = useMemo<NameSearchParams | null>(() => {
    if (!submittedParams) {
      return null;
    }
    return { ...submittedParams, limit: 50, offset };
  }, [offset, submittedParams]);

  const nameQuery = useQuery({
    queryKey: ["name-search", params],
    queryFn: () => searchName(params!),
    enabled: Boolean(params)
  });

  const bulkMutation = useMutation({
    mutationFn: createCedulasJob,
    onSuccess: () => {
      setCedulasText("");
      navigate("/jobs");
    }
  });

  const bulkNombresMutation = useMutation({
    mutationFn: createNombresJob,
    onSuccess: () => {
      setNombresText("");
      navigate("/jobs");
    }
  });

  function submitCedula(event: FormEvent) {
    event.preventDefault();
    const clean = cedula.replace(/\D+/g, "");
    if (clean) {
      navigate(`/records/${clean}`);
    }
  }

  function submitName(event: FormEvent) {
    event.preventDefault();
    setOffset(0);
    setSubmittedParams({ apellido1, apellido2, nombre1, nombre2, mode });
  }

  function submitBulk(event: FormEvent) {
    event.preventDefault();
    if (cedulasText.trim()) {
      bulkMutation.mutate(cedulasText);
    }
  }

  function submitBulkNombres(event: FormEvent) {
    event.preventDefault();
    if (nombresText.trim()) {
      bulkNombresMutation.mutate(nombresText);
    }
  }

  async function handleFile(file: File | null) {
    if (!file) {
      return;
    }
    setCedulasText(await file.text());
  }

  async function handleNombresFile(file: File | null) {
    if (!file) {
      return;
    }
    setNombresText(await file.text());
  }

  const tabs: { id: SearchTab; label: string; icon: typeof Search }[] = [
    { id: "cedula", label: "Cedula", icon: Search },
    { id: "nombre", label: "Nombre", icon: UserSearch },
    { id: "lote", label: "Lote", icon: ListChecks }
  ];

  return (
    <div className="page-stack">
      <header className="page-header">
        <div>
          <p className="eyebrow">ANI + Claro + Lugares</p>
          <h1>Consultas</h1>
        </div>
      </header>

      <section className="search-hero">
        <div className="search-tabs" role="tablist" aria-label="Modo de busqueda">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                type="button"
                role="tab"
                aria-selected={activeTab === tab.id}
                className={activeTab === tab.id ? "active" : ""}
                onClick={() => setActiveTab(tab.id)}
              >
                <Icon size={17} />
                {tab.label}
              </button>
            );
          })}
        </div>

        {activeTab === "cedula" ? (
          <div className="search-tab-panel" role="tabpanel">
            <div className="panel-heading">
              <Search size={20} />
              <div>
                <h2>Cedula unica</h2>
                <p>Retorna identidad, ubicacion, contactos y datos raw.</p>
              </div>
            </div>
            <form className="form-stack" onSubmit={submitCedula}>
              <label>
                ANINuip
                <input
                  className="mono"
                  value={cedula}
                  onChange={(event) => setCedula(event.target.value)}
                  inputMode="numeric"
                  placeholder="Ej: 1234567890"
                />
              </label>
              <button className="primary-button" type="submit">
                <Search size={18} />
                Consultar
              </button>
            </form>
          </div>
        ) : null}

        {activeTab === "nombre" ? (
          <div className="search-tab-panel" role="tabpanel">
            <div className="panel-heading">
              <UserSearch size={20} />
              <div>
                <h2>Nombre y apellidos</h2>
                <p>Busqueda exacta o por prefijo. Maximo 200 resultados por pagina.</p>
              </div>
            </div>

            <form className="name-form" onSubmit={submitName}>
              <label>
                Apellido 1
                <input value={apellido1} onChange={(event) => setApellido1(event.target.value)} />
              </label>
              <label>
                Apellido 2
                <input value={apellido2} onChange={(event) => setApellido2(event.target.value)} />
              </label>
              <label>
                Nombre 1
                <input value={nombre1} onChange={(event) => setNombre1(event.target.value)} />
              </label>
              <label>
                Nombre 2
                <input value={nombre2} onChange={(event) => setNombre2(event.target.value)} />
              </label>
              <div className="segmented" role="group" aria-label="Modo de busqueda">
                <button type="button" className={mode === "prefix" ? "active" : ""} onClick={() => setMode("prefix")}>
                  Prefijo
                </button>
                <button type="button" className={mode === "exact" ? "active" : ""} onClick={() => setMode("exact")}>
                  Exacta
                </button>
              </div>
              <button className="primary-button" type="submit">
                <Search size={18} />
                Buscar
              </button>
            </form>

            {nameQuery.error ? <p className="error-text">{nameQuery.error.message}</p> : null}
            {nameQuery.isFetching ? <p className="muted-text">Buscando...</p> : null}
            {nameQuery.data ? (
              <div className="search-results">
                <div className="results-head">
                  <h3>Resultados</h3>
                  <span className="count-chip">
                    {nameQuery.data.items.length}
                    {nameQuery.data.has_more ? "+" : ""}
                  </span>
                </div>

                {nameQuery.data.items.length === 0 ? (
                  <div className="result-empty">Sin coincidencias para esa busqueda.</div>
                ) : (
                  <div className="result-list">
                    {nameQuery.data.items.map((item) => {
                      const ubicacion = item.lugar_nacimiento
                        ? `${item.lugar_nacimiento.ciudad || ""} ${item.lugar_nacimiento.depto || ""}`.trim()
                        : "";
                      const meta = [item.sexo, item.fecha_nacimiento].filter(Boolean).join(" · ");
                      return (
                        <Link key={item.aninuip} className="result-card" to={`/records/${item.aninuip}`}>
                          <span className="result-avatar">{nameInitials(item.full_name)}</span>
                          <div className="result-main">
                            <p className="result-name">{item.full_name || "Sin nombre"}</p>
                            <p className="result-meta">{meta || "Sin datos"}</p>
                          </div>
                          <span className="result-id">{item.aninuip}</span>
                          <span className="result-loc">
                            <MapPin size={15} />
                            <span>{ubicacion || "—"}</span>
                          </span>
                          <span className="result-chev">
                            <ChevronRight size={18} />
                          </span>
                        </Link>
                      );
                    })}
                  </div>
                )}

                <div className="pagination">
                  <button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 50))} type="button">
                    Anterior
                  </button>
                  <span className="mono">Offset {offset}</span>
                  <button disabled={!nameQuery.data.has_more} onClick={() => setOffset(offset + 50)} type="button">
                    Siguiente
                  </button>
                </div>
              </div>
            ) : null}
          </div>
        ) : null}

        {activeTab === "lote" ? (
          <div className="search-tab-panel" role="tabpanel">
            <div className="panel-heading">
              <ListChecks size={20} />
              <div>
                <h2>Busqueda masiva</h2>
                <p>Crea un job que se procesa en segundo plano y genera CSV/XLSX.</p>
              </div>
            </div>

            <div className="segmented lote-toggle" role="group" aria-label="Tipo de lote">
              <button type="button" className={loteMode === "cedulas" ? "active" : ""} onClick={() => setLoteMode("cedulas")}>
                Cedulas
              </button>
              <button type="button" className={loteMode === "nombres" ? "active" : ""} onClick={() => setLoteMode("nombres")}>
                Nombres
              </button>
            </div>

            {loteMode === "cedulas" ? (
              <form className="form-stack" onSubmit={submitBulk}>
                <textarea
                  value={cedulasText}
                  onChange={(event) => setCedulasText(event.target.value)}
                  placeholder="123&#10;456&#10;789"
                  rows={6}
                />
                <p className="muted-text">Pega o carga un archivo separado por lineas, comas o espacios.</p>
                <div className="inline-actions">
                  <label className="file-button">
                    <FileUp size={17} />
                    Archivo
                    <input
                      type="file"
                      accept=".txt,.csv"
                      onChange={(event) => handleFile(event.target.files?.[0] || null)}
                    />
                  </label>
                  <button className="primary-button" disabled={bulkMutation.isPending} type="submit">
                    <ListChecks size={18} />
                    {bulkMutation.isPending ? "Creando..." : "Crear job"}
                  </button>
                </div>
                {bulkMutation.error ? <p className="error-text">{bulkMutation.error.message}</p> : null}
              </form>
            ) : (
              <form className="form-stack" onSubmit={submitBulkNombres}>
                <textarea
                  value={nombresText}
                  onChange={(event) => setNombresText(event.target.value)}
                  placeholder={"PEREZ GOMEZ JUAN CARLOS\nRAMIREZ;DIAZ;MARIA;JOSE\nLOPEZ TORRES, ANA"}
                  rows={6}
                />
                <p className="muted-text">
                  Acepta 1 columna (nombre completo), 2 columnas (apellidos | nombres) o 4 columnas
                  (apellido1 | apellido2 | nombre1 | nombre2). Separadores: tab, ";", "|" o ",".
                </p>
                <div className="inline-actions">
                  <label className="file-button">
                    <FileUp size={17} />
                    Archivo
                    <input
                      type="file"
                      accept=".txt,.csv"
                      onChange={(event) => handleNombresFile(event.target.files?.[0] || null)}
                    />
                  </label>
                  <button className="primary-button" disabled={bulkNombresMutation.isPending} type="submit">
                    <ListChecks size={18} />
                    {bulkNombresMutation.isPending ? "Creando..." : "Crear job"}
                  </button>
                </div>
                {bulkNombresMutation.error ? (
                  <p className="error-text">{bulkNombresMutation.error.message}</p>
                ) : null}
              </form>
            )}
          </div>
        ) : null}
      </section>
    </div>
  );
}
