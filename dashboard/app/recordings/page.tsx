import { supabase } from "@/lib/supabase";
import Link from "next/link";
import { StatusBadge } from "../components/StatusBadge";

export const dynamic = "force-dynamic";

const FILTERS = [
  { key: "all", label: "All" },
  { key: "raw_uploaded", label: "Uploaded" },
  { key: "processing", label: "Processing" },
  { key: "processed", label: "Processed" },
  { key: "failed", label: "Failed" },
];

export default async function RecordingsPage({
  searchParams,
}: {
  searchParams: Promise<{ status?: string; page?: string }>;
}) {
  const params = await searchParams;
  const status = params.status || "all";
  const page = parseInt(params.page || "1", 10);
  const perPage = 50;
  const offset = (page - 1) * perPage;

  let query = supabase
    .from("recordings")
    .select(
      "id, status, duration_seconds, speech_yield, clip_count, speech_seconds, failure_reason, created_at",
      { count: "exact" },
    )
    // Keep rows with null failure_reason; only exclude archived Ateso phantom rows.
    .or("failure_reason.is.null,failure_reason.not.ilike.%phantom%")
    .order("created_at", { ascending: false })
    .range(offset, offset + perPage - 1);

  if (status !== "all") {
    query = query.eq("status", status);
  }

  const { data: recordings, count } = await query;
  const totalPages = Math.ceil((count ?? 0) / perPage);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-end justify-between gap-4">
        <div>
          <h1 className="text-[28px] leading-tight font-semibold tracking-tight">
            Recordings
          </h1>
          <p className="mt-1 text-sm text-fg-muted">
            Every recording ingested into the pipeline, newest first.
          </p>
        </div>
        <span className="text-sm text-fg-muted tabular-nums">
          {count?.toLocaleString() ?? 0} total
        </span>
      </div>

      {/* Filter chips */}
      <div className="flex flex-wrap gap-1.5">
        {FILTERS.map((f) => {
          const active = status === f.key;
          return (
            <Link
              key={f.key}
              href={`/recordings?status=${f.key}`}
              className={`inline-flex items-center rounded-full border px-3 py-1 text-xs transition-colors ${
                active
                  ? "bg-fg text-bg border-fg"
                  : "border-border text-fg-muted hover:border-border-strong hover:text-fg"
              }`}
            >
              {f.label}
            </Link>
          );
        })}
      </div>

      {/* Table */}
      <div className="rounded-xl border border-border bg-surface overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left border-b border-border">
                <th className="px-4 py-3 text-[11px] font-medium text-fg-muted uppercase tracking-[0.08em]">
                  ID
                </th>
                <th className="px-4 py-3 text-[11px] font-medium text-fg-muted uppercase tracking-[0.08em]">
                  Status
                </th>
                <th className="px-4 py-3 text-[11px] font-medium text-fg-muted uppercase tracking-[0.08em]">
                  Duration
                </th>
                <th className="px-4 py-3 text-[11px] font-medium text-fg-muted uppercase tracking-[0.08em]">
                  Yield
                </th>
                <th className="px-4 py-3 text-[11px] font-medium text-fg-muted uppercase tracking-[0.08em]">
                  Clips
                </th>
                <th className="px-4 py-3 text-[11px] font-medium text-fg-muted uppercase tracking-[0.08em]">
                  Speech
                </th>
                <th className="px-4 py-3 text-[11px] font-medium text-fg-muted uppercase tracking-[0.08em]">
                  Created
                </th>
              </tr>
            </thead>
            <tbody>
              {(recordings ?? []).length === 0 ? (
                <tr>
                  <td
                    colSpan={7}
                    className="px-4 py-10 text-center text-sm text-fg-subtle"
                  >
                    No recordings match this filter.
                  </td>
                </tr>
              ) : (
                (recordings ?? []).map((r) => (
                  <tr
                    key={r.id}
                    className="border-b border-border last:border-0 hover:bg-surface-hover transition-colors"
                  >
                    <td className="px-4 py-2.5 font-mono text-xs text-fg-muted">
                      {r.id.slice(0, 8)}
                    </td>
                    <td className="px-4 py-2.5">
                      <StatusBadge status={r.status} />
                    </td>
                    <td className="px-4 py-2.5 tabular-nums text-fg-muted">
                      {r.duration_seconds
                        ? `${(r.duration_seconds / 60).toFixed(0)}m`
                        : "—"}
                    </td>
                    <td className="px-4 py-2.5 tabular-nums">
                      {r.speech_yield != null ? (
                        <span
                          className={
                            r.speech_yield > 0.5
                              ? "text-success"
                              : r.speech_yield > 0.2
                                ? "text-warning"
                                : "text-danger"
                          }
                        >
                          {(r.speech_yield * 100).toFixed(1)}%
                        </span>
                      ) : (
                        <span className="text-fg-subtle">—</span>
                      )}
                    </td>
                    <td className="px-4 py-2.5 tabular-nums text-fg">
                      {r.clip_count ?? "—"}
                    </td>
                    <td className="px-4 py-2.5 tabular-nums text-fg-muted">
                      {r.speech_seconds
                        ? `${(r.speech_seconds / 60).toFixed(0)}m`
                        : "—"}
                    </td>
                    <td className="px-4 py-2.5 text-xs text-fg-subtle">
                      {r.created_at
                        ? new Date(r.created_at).toLocaleDateString()
                        : "—"}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          {page > 1 ? (
            <Link
              href={`/recordings?status=${status}&page=${page - 1}`}
              className="px-3 py-1.5 text-xs rounded-md border border-border text-fg-muted hover:text-fg hover:border-border-strong transition-colors"
            >
              ← Prev
            </Link>
          ) : (
            <span className="px-3 py-1.5 text-xs rounded-md border border-border text-fg-subtle opacity-50 cursor-default">
              ← Prev
            </span>
          )}
          <span className="px-3 py-1.5 text-xs text-fg-muted tabular-nums">
            Page {page} of {totalPages}
          </span>
          {page < totalPages ? (
            <Link
              href={`/recordings?status=${status}&page=${page + 1}`}
              className="px-3 py-1.5 text-xs rounded-md border border-border text-fg-muted hover:text-fg hover:border-border-strong transition-colors"
            >
              Next →
            </Link>
          ) : (
            <span className="px-3 py-1.5 text-xs rounded-md border border-border text-fg-subtle opacity-50 cursor-default">
              Next →
            </span>
          )}
        </div>
      )}
    </div>
  );
}
