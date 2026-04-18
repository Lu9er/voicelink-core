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
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-end justify-between gap-4">
        <div>
          <h1 className="text-[36px] leading-tight font-bold tracking-tight text-primary font-[family-name:var(--font-headline)]">
            Recordings
          </h1>
          <p className="mt-2 text-sm text-fg-muted font-[family-name:var(--font-body)]">
            Every recording ingested into the pipeline, newest first.
          </p>
        </div>
        <span className="text-sm text-fg-muted tabular-nums font-[family-name:var(--font-label)]">
          {count?.toLocaleString() ?? 0} total
        </span>
      </div>

      {/* Filter chips */}
      <div className="flex flex-wrap gap-2">
        {FILTERS.map((f) => {
          const active = status === f.key;
          return (
            <Link
              key={f.key}
              href={`/recordings?status=${f.key}`}
              className={`inline-flex items-center rounded-full px-4 py-1.5 text-xs font-medium transition-colors font-[family-name:var(--font-body)] ${
                active
                  ? "bg-primary text-white"
                  : "bg-surface-low text-fg-muted hover:bg-surface-container hover:text-fg"
              }`}
            >
              {f.label}
            </Link>
          );
        })}
      </div>

      {/* Table */}
      <div className="rounded-2xl bg-surface-lowest overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left bg-surface-low">
                <th className="px-5 py-3.5 text-[11px] font-medium text-fg-muted uppercase tracking-[0.08em] font-[family-name:var(--font-body)]">
                  ID
                </th>
                <th className="px-5 py-3.5 text-[11px] font-medium text-fg-muted uppercase tracking-[0.08em] font-[family-name:var(--font-body)]">
                  Status
                </th>
                <th className="px-5 py-3.5 text-[11px] font-medium text-fg-muted uppercase tracking-[0.08em] font-[family-name:var(--font-body)]">
                  Duration
                </th>
                <th className="px-5 py-3.5 text-[11px] font-medium text-fg-muted uppercase tracking-[0.08em] font-[family-name:var(--font-body)]">
                  Yield
                </th>
                <th className="px-5 py-3.5 text-[11px] font-medium text-fg-muted uppercase tracking-[0.08em] font-[family-name:var(--font-body)]">
                  Clips
                </th>
                <th className="px-5 py-3.5 text-[11px] font-medium text-fg-muted uppercase tracking-[0.08em] font-[family-name:var(--font-body)]">
                  Speech
                </th>
                <th className="px-5 py-3.5 text-[11px] font-medium text-fg-muted uppercase tracking-[0.08em] font-[family-name:var(--font-body)]">
                  Created
                </th>
              </tr>
            </thead>
            <tbody>
              {(recordings ?? []).length === 0 ? (
                <tr>
                  <td
                    colSpan={7}
                    className="px-5 py-12 text-center text-sm text-fg-subtle"
                  >
                    No recordings match this filter.
                  </td>
                </tr>
              ) : (
                (recordings ?? []).map((r, i) => (
                  <tr
                    key={r.id}
                    className={`transition-colors hover:bg-surface-hover ${
                      i % 2 === 1 ? "bg-surface-low/50" : ""
                    }`}
                  >
                    <td className="px-5 py-3 text-xs text-fg-muted font-[family-name:var(--font-label)]">
                      {r.id.slice(0, 8)}
                    </td>
                    <td className="px-5 py-3">
                      <StatusBadge status={r.status} />
                    </td>
                    <td className="px-5 py-3 tabular-nums text-fg-muted font-[family-name:var(--font-label)]">
                      {r.duration_seconds
                        ? `${(r.duration_seconds / 60).toFixed(0)}m`
                        : "--"}
                    </td>
                    <td className="px-5 py-3 tabular-nums font-[family-name:var(--font-label)]">
                      {r.speech_yield != null ? (
                        <span
                          className={
                            r.speech_yield > 0.5
                              ? "text-tertiary"
                              : r.speech_yield > 0.2
                                ? "text-warning"
                                : "text-danger"
                          }
                        >
                          {(r.speech_yield * 100).toFixed(1)}%
                        </span>
                      ) : (
                        <span className="text-fg-subtle">--</span>
                      )}
                    </td>
                    <td className="px-5 py-3 tabular-nums text-fg font-[family-name:var(--font-label)]">
                      {r.clip_count ?? "--"}
                    </td>
                    <td className="px-5 py-3 tabular-nums text-fg-muted font-[family-name:var(--font-label)]">
                      {r.speech_seconds
                        ? `${(r.speech_seconds / 60).toFixed(0)}m`
                        : "--"}
                    </td>
                    <td className="px-5 py-3 text-xs text-fg-subtle font-[family-name:var(--font-body)]">
                      {r.created_at
                        ? new Date(r.created_at).toLocaleDateString()
                        : "--"}
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
        <div className="flex items-center justify-center gap-3">
          {page > 1 ? (
            <Link
              href={`/recordings?status=${status}&page=${page - 1}`}
              className="px-4 py-2 text-xs rounded-lg bg-surface-low text-fg-muted hover:text-fg hover:bg-surface-container transition-colors font-[family-name:var(--font-body)]"
            >
              Prev
            </Link>
          ) : (
            <span className="px-4 py-2 text-xs rounded-lg bg-surface-low text-fg-subtle opacity-50 cursor-default font-[family-name:var(--font-body)]">
              Prev
            </span>
          )}
          <span className="px-3 py-2 text-xs text-fg-muted tabular-nums font-[family-name:var(--font-label)]">
            Page {page} of {totalPages}
          </span>
          {page < totalPages ? (
            <Link
              href={`/recordings?status=${status}&page=${page + 1}`}
              className="px-4 py-2 text-xs rounded-lg bg-surface-low text-fg-muted hover:text-fg hover:bg-surface-container transition-colors font-[family-name:var(--font-body)]"
            >
              Next
            </Link>
          ) : (
            <span className="px-4 py-2 text-xs rounded-lg bg-surface-low text-fg-subtle opacity-50 cursor-default font-[family-name:var(--font-body)]">
              Next
            </span>
          )}
        </div>
      )}
    </div>
  );
}
