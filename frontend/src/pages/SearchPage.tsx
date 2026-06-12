import { useMutation, useQuery } from "@tanstack/react-query";
import { FileUp, ListChecks, Search, UserSearch } from "lucide-react";
import { FormEvent, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { createCedulasJob, NameSearchParams, searchName } from "../api/client";

type SearchMode = "prefix" | "exact";

export function SearchPage() {
  const navigate = useNavigate();
  const [cedula, setCedula] = useState("");
  const [apellido1, setApellido1] = useState("");
  const [apellido2, setApellido2] = useState("");
  const [nombre1, setNombre1] = useState("");
  const [nombre2, setNombre2] = useState("");
  const [mode, setMode] = useState<SearchMode>("prefix");
  const [offset, setOffset] = useState(0);
  const [submittedParams, setSubmittedParams] = useState<NameSearchParams | null>(null);
  const [cedulasText, setCedulasText] = useState("");

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

  async function handleFile(file: File | null) {
    if (!file) {
      return;
    }
    setCedulasText(await file.text());
  }

  return (
    <div className="page-stack">
      <header className="page-header">
        <div>
          <p className="eyebrow">ANI + Claro + Lugares</p>
          <h1>Consultas</h1>
        </div>
      </header>

      <section className="tool-grid">
        <form className="panel" onSubmit={submitCedula}>
          <div className="panel-heading">
            <Search size={20} />
            <div>
              <h2>Cedula unica</h2>
              <p>Retorna identidad, ubicacion, contactos y datos raw.</p>
            </div>
          </div>
          <label>
            ANINuip
            <input
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

        <form className="panel" onSubmit={submitBulk}>
          <div className="panel-heading">
            <FileUp size={20} />
            <div>
              <h2>Lote de cedulas</h2>
              <p>Pega o carga un archivo separado por lineas, comas o espacios.</p>
            </div>
          </div>
          <textarea
            value={cedulasText}
            onChange={(event) => setCedulasText(event.target.value)}
            placeholder="123&#10;456&#10;789"
            rows={6}
          />
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
      </section>

      <section className="panel">
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
          <>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>ANINuip</th>
                    <th>Nombre completo</th>
                    <th>Sexo</th>
                    <th>Nacimiento</th>
                    <th>Ubicacion</th>
                  </tr>
                </thead>
                <tbody>
                  {nameQuery.data.items.map((item) => (
                    <tr key={item.aninuip}>
                      <td>
                        <Link to={`/records/${item.aninuip}`}>{item.aninuip}</Link>
                      </td>
                      <td>{item.full_name}</td>
                      <td>{item.sexo || "-"}</td>
                      <td>{item.fecha_nacimiento || "-"}</td>
                      <td>
                        {item.lugar_nacimiento
                          ? `${item.lugar_nacimiento.ciudad || ""} ${item.lugar_nacimiento.depto || ""}`
                          : "-"}
                      </td>
                    </tr>
                  ))}
                  {nameQuery.data.items.length === 0 ? (
                    <tr>
                      <td colSpan={5}>Sin resultados</td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
            <div className="pagination">
              <button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 50))} type="button">
                Anterior
              </button>
              <span>Offset {offset}</span>
              <button disabled={!nameQuery.data.has_more} onClick={() => setOffset(offset + 50)} type="button">
                Siguiente
              </button>
            </div>
          </>
        ) : null}
      </section>
    </div>
  );
}
