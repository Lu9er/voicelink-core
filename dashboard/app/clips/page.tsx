import { supabase } from "@/lib/supabase";
import Link from "next/link";
import { StatusBadge } from "../components/StatusBadge";

export const dynamic = "force-dynamic";

export default async function ClipsPage({
  searchParams,
}: {
  searchParams: Promise<{ status?: string; page?: string }>;
}) {
  const params = await searchParams;
  const status = params.status || "all";
  const page = parseInt(params.page || "1", 10);
  const perPage = 50;
  const offset = (page - 1) * perPage;

  const statusList = ["pending_review", "approved", "rejected"] as const;
  const counts: Record<string, number> = {};
  let totalAll = 0;
  for (const s of statusList) {
    const { count } = await supabase
      .from("clips")
      .select("*", { count: "exact", head: true })
      .eq("status", s);
    counts[s] = count ?? 0;
    totalAll += count ?? 0;
  }

  let query = supabase
    .from("clips")
    .select(
      "id, recording_id, gcs_clip_url, duration_seconds, status, transcript, created_at",
      { count: "exact" },
    )
    .order("created_at", { ascending: false })
    .range(offset, offset + perPage - 1);

  if (status !== "all") {
    query = query.eq("status", status);
  }

  const { data: clips, count } = await query;
  const totalPages = Math.ceil((count ?? 0) / perPage);

  const filters = [
    { key: "all", label: "All", count: totalAll },
    { key: "pending_review", label: "Pending review", count: counts.pending_review ?? 0 },
    { key: "approved", label: "Approved", count: counts.approved ?? 0 },
    { key: "rejected", label: "Rejected", count: counts.rejected ?? 0 },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-end justify-between gap-4">
        <div>
          <h1 className="text-[28px] leading-tight font-semibold tracking-tight">
            Clips
          </h1>
          <p className="mt-1 text-sm text-fg-muted">
            Segmented speech extracted from processed recordings.
          </p>
        </div>
        <span className="text-sm text-fg-muted tabular-nums">
          {totalAll.toLocaleString()} total
        </span>
      </div>

      {/* Filter chips with counts */}
      <div className="flex flex-wrap gap-1.5">
        {filters.map((f) => {
          const active = status === f.key;
          return (
            <Link
              key={f.key}
              href={`/clips?status=${f.key}`}
              className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs transition-colors ${
                active
                  ? "bg-fg text-bg border-fg"
                  : "border-border text-fg-muted hover:border-border-strong hover:text-fg"
              }`}
            >
              <span>{f.label}</span>
              <span
                className={`text-[10px] tabular-nums rounded-full px-1.5 py-0.5 ${
                  active
                    ? "bg-bg/20 text-bg"
                    : "bg-surface-elev text-fg-subtle"
                }`}
              >
                {f.count.toLocaleString()}
              </span>
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
                  Clip ID
                </th>
                <th className="px-4 py-3 text-[11px] font-medium text-fg-muted uppercase tracking-[0.08em]">
                  Recording
                </th>
                <th className="px-4 py-3 text-[11px] font-medium text-fg-muted uppercase tracking-[0.08em]">
                  Duration
                </th>
                <th className="px-4 py-3 text-[11px] font-medium text-fg-muted uppercase tracking-[0.08em]">
                  Status
                </th>
                <th className="px-4 py-3 text-[11px] font-medium text-fg-muted uppercase tracking-[0.08em]">
                  Transcript
                </th>
                <th className="px-4 py-3 text-[11px] font-medium text-fg-muted uppercase tracking-[0.08em]">
                  Created
                </th>
              </tr>
            </thead>
            <tbody>
              {(clips ?? []).length === 0 ? (
                <tr>
                  <td
                    colSpan={6}
                    className="px-4 py-10 text-center text-sm text-fg-subtle"
                  >
                    No clips match this filter.
                  </td>
                </tr>
              ) : (
                (clips ?? []).map((c) => (
                  <tr
                    key={c.id}
                    className="border-b border-border last:border-0 hover:bg-surface-hover transition-colors"
                  >
                    <td className="px-4 py-2.5 font-mono text-xs text-fg-muted">
                      {c.id.slice(0, 8)}
                    </td>
                    <td className="px-4 py-2.5 font-mono text-xs text-fg-subtle">
                      {c.recording_id.slice(0, 8)}
                    </td>
                    <td className="px-4 py-2.5 tabular-nums text-fg-muted">
                      {c.duration_seconds?.toFixed(1)}s
                    </td>
                    <td className="px-4 py-2.5">
                      <StatusBadge status={c.status} />
                    </td>
                    <td className="px-4 py-2.5 text-xs text-fg-muted max-w-sm truncate">
                      {c.transcript ?? (
                        <span className="text-fg-subtle italic">
                          No transcript
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-2.5 text-xs text-fg-subtle whitespace-nowrap">
                      {c.created_at
                        ? new Date(c.created_at).toLocaleDateString()
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
              href={`/clips?status=${status}&page=${page - 1}`}
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
              href={`/clips?status=${status}&page=${page + 1}`}
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
