import { useMutation, useQuery } from "@tanstack/react-query";
import { Download, RefreshCw } from "lucide-react";

import { downloadJob, listJobs } from "../api/client";

function statusLabel(status: string) {
  const labels: Record<string, string> = {
    queued: "En cola",
    running: "Procesando",
    done: "Listo",
    failed: "Fallido"
  };
  return labels[status] || status;
}

export function JobsPage() {
  const jobsQuery = useQuery({
    queryKey: ["jobs"],
    queryFn: listJobs,
    refetchInterval: 3000
  });
  const downloadMutation = useMutation({
    mutationFn: ({ jobId, format }: { jobId: string; format: "csv" | "xlsx" }) => downloadJob(jobId, format)
  });

  return (
    <div className="page-stack">
      <header className="page-header">
        <div>
          <p className="eyebrow">Procesamiento asincrono</p>
          <h1>Jobs</h1>
        </div>
        <button className="icon-text-button" type="button" onClick={() => jobsQuery.refetch()}>
          <RefreshCw size={17} />
          Actualizar
        </button>
      </header>

      {jobsQuery.error ? <p className="error-text">{jobsQuery.error.message}</p> : null}
      {downloadMutation.error ? <p className="error-text">{downloadMutation.error.message}</p> : null}

      <section className="panel">
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Creado</th>
                <th>Tipo</th>
                <th>Estado</th>
                <th>Progreso</th>
                <th>Encontrados</th>
                <th>Descarga</th>
              </tr>
            </thead>
            <tbody>
              {jobsQuery.data?.map((job) => {
                const progress = job.unique_count ? Math.round((job.processed_count / job.unique_count) * 100) : 0;
                return (
                  <tr key={job.id}>
                    <td>{new Date(job.created_at).toLocaleString()}</td>
                    <td>{job.kind}</td>
                    <td>
                      <span className={`status-chip ${job.status}`}>{statusLabel(job.status)}</span>
                      {job.error ? <small className="error-inline">{job.error}</small> : null}
                    </td>
                    <td>
                      <div className="progress-line">
                        <span style={{ width: `${Math.min(progress, 100)}%` }} />
                      </div>
                      <small>
                        {job.processed_count} / {job.unique_count}
                      </small>
                    </td>
                    <td>{job.result_count}</td>
                    <td>
                      <div className="inline-actions">
                        <button
                          className="icon-button"
                          disabled={!job.has_csv || job.status !== "done"}
                          title="Descargar CSV"
                          type="button"
                          onClick={() => downloadMutation.mutate({ jobId: job.id, format: "csv" })}
                        >
                          <Download size={17} />
                          CSV
                        </button>
                        <button
                          className="icon-button"
                          disabled={!job.has_xlsx || job.status !== "done"}
                          title="Descargar XLSX"
                          type="button"
                          onClick={() => downloadMutation.mutate({ jobId: job.id, format: "xlsx" })}
                        >
                          <Download size={17} />
                          XLSX
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
              {jobsQuery.data?.length === 0 ? (
                <tr>
                  <td colSpan={6}>Aun no hay jobs</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
