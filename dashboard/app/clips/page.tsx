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
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-end justify-between gap-4">
        <div>
          <h1 className="text-[36px] leading-tight font-bold tracking-tight text-primary font-[family-name:var(--font-headline)]">
            Clips
          </h1>
          <p className="mt-2 text-sm text-fg-muted font-[family-name:var(--font-body)]">
            Segmented speech extracted from processed recordings.
          </p>
        </div>
        <span className="text-sm text-fg-muted tabular-nums font-[family-name:var(--font-label)]">
          {totalAll.toLocaleString()} total
        </span>
      </div>

      {/* Filter chips with counts */}
      <div className="flex flex-wrap gap-2">
        {filters.map((f) => {
          const active = status === f.key;
          return (
            <Link
              key={f.key}
              href={`/clips?status=${f.key}`}
              className={`inline-flex items-center gap-2 rounded-full px-4 py-1.5 text-xs font-medium transition-colors font-[family-name:var(--font-body)] ${
                active
                  ? "bg-primary text-white"
                  : "bg-surface-low text-fg-muted hover:bg-surface-container hover:text-fg"
              }`}
            >
              <span>{f.label}</span>
              <span
                className={`text-[10px] tabular-nums rounded-full px-1.5 py-0.5 font-[family-name:var(--font-label)] ${
                  active
                    ? "bg-white/20 text-white"
                    : "bg-surface-container text-fg-subtle"
                }`}
              >
                {f.count.toLocaleString()}
              </span>
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
                  Clip ID
                </th>
                <th className="px-5 py-3.5 text-[11px] font-medium text-fg-muted uppercase tracking-[0.08em] font-[family-name:var(--font-body)]">
                  Recording
                </th>
                <th className="px-5 py-3.5 text-[11px] font-medium text-fg-muted uppercase tracking-[0.08em] font-[family-name:var(--font-body)]">
                  Duration
                </th>
                <th className="px-5 py-3.5 text-[11px] font-medium text-fg-muted uppercase tracking-[0.08em] font-[family-name:var(--font-body)]">
                  Status
                </th>
                <th className="px-5 py-3.5 text-[11px] font-medium text-fg-muted uppercase tracking-[0.08em] font-[family-name:var(--font-body)]">
                  Transcript
                </th>
                <th className="px-5 py-3.5 text-[11px] font-medium text-fg-muted uppercase tracking-[0.08em] font-[family-name:var(--font-body)]">
                  Created
                </th>
              </tr>
            </thead>
            <tbody>
              {(clips ?? []).length === 0 ? (
                <tr>
                  <td
                    colSpan={6}
                    className="px-5 py-12 text-center text-sm text-fg-subtle"
                  >
                    No clips match this filter.
                  </td>
                </tr>
              ) : (
                (clips ?? []).map((c, i) => (
                  <tr
                    key={c.id}
                    className={`transition-colors hover:bg-surface-hover ${
                      i % 2 === 1 ? "bg-surface-low/50" : ""
                    }`}
                  >
                    <td className="px-5 py-3 text-xs text-fg-muted font-[family-name:var(--font-label)]">
                      {c.id.slice(0, 8)}
                    </td>
                    <td className="px-5 py-3 text-xs text-fg-subtle font-[family-name:var(--font-label)]">
                      {c.recording_id.slice(0, 8)}
                    </td>
                    <td className="px-5 py-3 tabular-nums text-fg-muted font-[family-name:var(--font-label)]">
                      {c.duration_seconds?.toFixed(1)}s
                    </td>
                    <td className="px-5 py-3">
                      <StatusBadge status={c.status} />
                    </td>
                    <td className="px-5 py-3 text-xs text-fg-muted max-w-sm truncate font-[family-name:var(--font-body)]">
                      {c.transcript ?? (
                        <span className="text-fg-subtle italic">
                          No transcript
                        </span>
                      )}
                    </td>
                    <td className="px-5 py-3 text-xs text-fg-subtle whitespace-nowrap font-[family-name:var(--font-body)]">
                      {c.created_at
                        ? new Date(c.created_at).toLocaleDateString()
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
              href={`/clips?status=${status}&page=${page - 1}`}
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
              href={`/clips?status=${status}&page=${page + 1}`}
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
