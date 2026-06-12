import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Database, MapPinned, Phone, UserRound } from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { getRecord } from "../api/client";

type TabName = "resumen" | "contacto" | "raw";

function formatValue(value: unknown) {
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  if (typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value);
}

export function RecordPage() {
  const { aninuip = "" } = useParams();
  const [tab, setTab] = useState<TabName>("resumen");
  const query = useQuery({
    queryKey: ["record", aninuip],
    queryFn: () => getRecord(aninuip),
    enabled: Boolean(aninuip)
  });

  return (
    <div className="page-stack">
      <Link className="back-link" to="/">
        <ArrowLeft size={17} />
        Volver
      </Link>

      {query.isLoading ? <p className="muted-text">Cargando registro...</p> : null}
      {query.error ? <p className="error-text">{query.error.message}</p> : null}

      {query.data ? (
        <>
          <header className="record-header">
            <div>
              <p className="eyebrow">ANINuip {query.data.aninuip}</p>
              <h1>{query.data.full_name || "Registro sin nombre"}</h1>
            </div>
            <div className="status-chip">Completo</div>
          </header>

          <div className="tabbar">
            <button className={tab === "resumen" ? "active" : ""} onClick={() => setTab("resumen")} type="button">
              <UserRound size={17} />
              Resumen
            </button>
            <button className={tab === "contacto" ? "active" : ""} onClick={() => setTab("contacto")} type="button">
              <Phone size={17} />
              Contacto
            </button>
            <button className={tab === "raw" ? "active" : ""} onClick={() => setTab("raw")} type="button">
              <Database size={17} />
              Raw
            </button>
          </div>

          {tab === "resumen" ? (
            <section className="detail-grid">
              <div className="panel">
                <div className="panel-heading">
                  <UserRound size={20} />
                  <h2>Identidad</h2>
                </div>
                <div className="definition-grid">
                  {Object.entries(query.data.identity).map(([key, value]) => (
                    <div key={key}>
                      <dt>{key}</dt>
                      <dd>{formatValue(value)}</dd>
                    </div>
                  ))}
                </div>
              </div>

              <div className="panel">
                <div className="panel-heading">
                  <MapPinned size={20} />
                  <h2>Ubicaciones</h2>
                </div>
                <div className="definition-grid">
                  {Object.entries(query.data.locations).map(([key, value]) => (
                    <div key={key}>
                      <dt>{key}</dt>
                      <dd>{value ? `${value.ciudad || "-"} / ${value.depto || "-"} (${value.code || "-"})` : "-"}</dd>
                    </div>
                  ))}
                </div>
              </div>
            </section>
          ) : null}

          {tab === "contacto" ? (
            <section className="panel">
              <div className="panel-heading">
                <Phone size={20} />
                <h2>Contactos Claro 2017</h2>
              </div>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Cedula</th>
                      <th>Celular</th>
                      <th>Nombre</th>
                      <th>Direccion</th>
                      <th>Ciudad</th>
                    </tr>
                  </thead>
                  <tbody>
                    {query.data.contacts.map((contact, index) => (
                      <tr key={`${contact.cedula}-${index}`}>
                        <td>{contact.cedula}</td>
                        <td>{contact.cel || "-"}</td>
                        <td>{contact.nombre || "-"}</td>
                        <td>{contact.dir || "-"}</td>
                        <td>{contact.ciud || "-"}</td>
                      </tr>
                    ))}
                    {query.data.contacts.length === 0 ? (
                      <tr>
                        <td colSpan={5}>Sin contactos</td>
                      </tr>
                    ) : null}
                  </tbody>
                </table>
              </div>
            </section>
          ) : null}

          {tab === "raw" ? (
            <section className="panel">
              <div className="panel-heading">
                <Database size={20} />
                <h2>Columnas completas</h2>
              </div>
              <div className="raw-grid">
                {Object.entries(query.data.raw).map(([key, value]) => (
                  <div key={key}>
                    <dt>{key}</dt>
                    <dd>{formatValue(value)}</dd>
                  </div>
                ))}
              </div>
            </section>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
