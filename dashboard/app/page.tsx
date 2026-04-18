import { supabase } from "@/lib/supabase";
import { StatCard } from "./components/StatCard";
import { PipelineFlow } from "./components/PipelineFlow";
import { Section } from "./components/Section";

export const dynamic = "force-dynamic";

async function getStats() {
  const statuses = [
    "raw_uploaded",
    "processing",
    "processed",
    "failed",
  ] as const;
  const statusCounts: Record<string, number> = {};
  for (const s of statuses) {
    const { count } = await supabase
      .from("recordings")
      .select("*", { count: "exact", head: true })
      .eq("status", s);
    statusCounts[s] = count ?? 0;
  }

  // Real failures exclude archived Ateso phantom rows
  const { count: realFailedCount } = await supabase
    .from("recordings")
    .select("*", { count: "exact", head: true })
    .eq("status", "failed")
    .not("failure_reason", "like", "%phantom%");

  const clipStatuses = ["pending_review", "approved", "rejected"] as const;
  const clipCounts: Record<string, number> = {};
  let totalClips = 0;
  for (const s of clipStatuses) {
    const { count } = await supabase
      .from("clips")
      .select("*", { count: "exact", head: true })
      .eq("status", s);
    clipCounts[s] = count ?? 0;
    totalClips += count ?? 0;
  }

  const { data: speechData } = await supabase
    .from("recordings")
    .select("speech_seconds")
    .eq("status", "processed");
  const totalSpeechSeconds = (speechData ?? []).reduce(
    (sum, r) => sum + (r.speech_seconds ?? 0),
    0,
  );

  const { data: recentProcessed } = await supabase
    .from("recordings")
    .select("id, speech_yield, clip_count, speech_seconds, updated_at")
    .eq("status", "processed")
    .order("updated_at", { ascending: false })
    .limit(8);

  const { data: recentFailed } = await supabase
    .from("recordings")
    .select("id, failure_reason, updated_at")
    .eq("status", "failed")
    .not("failure_reason", "like", "%phantom%")
    .order("updated_at", { ascending: false })
    .limit(5);

  return {
    statusCounts,
    realFailedCount: realFailedCount ?? 0,
    archivedCount:
      (statusCounts.failed ?? 0) - (realFailedCount ?? 0),
    clipCounts,
    totalClips,
    totalSpeechHours: totalSpeechSeconds / 3600,
    recentProcessed: recentProcessed ?? [],
    recentFailed: recentFailed ?? [],
  };
}

function yieldTone(y: number): "success" | "warning" | "danger" {
  if (y > 0.5) return "success";
  if (y > 0.2) return "warning";
  return "danger";
}

function YieldPill({ value }: { value: number }) {
  const tone = yieldTone(value);
  const cls =
    tone === "success"
      ? "bg-success-soft text-tertiary"
      : tone === "warning"
        ? "bg-warning-soft text-warning"
        : "bg-danger-soft text-danger";
  return (
    <span
      className={`inline-flex items-center rounded-md px-1.5 py-0.5 text-[11px] font-medium tabular-nums font-[family-name:var(--font-label)] ${cls}`}
    >
      {(value * 100).toFixed(1)}%
    </span>
  );
}

export default async function OverviewPage() {
  const stats = await getStats();

  return (
    <div className="space-y-12">
      {/* Hero */}
      <div className="flex flex-col gap-3">
        <p className="text-xs font-medium text-secondary uppercase tracking-[0.12em] font-[family-name:var(--font-body)]">
          VoiceLink Uganda
        </p>
        <h1 className="text-[36px] leading-tight font-bold tracking-tight text-primary font-[family-name:var(--font-headline)]">
          Ingestion Overview
        </h1>
        <p className="text-sm text-fg-muted max-w-2xl font-[family-name:var(--font-body)]">
          Live view of recordings entering the pipeline, their processing
          state, and the clips produced for quality review.
        </p>
      </div>

      {/* Pipeline flow */}
      <PipelineFlow
        stages={[
          {
            label: "Uploaded",
            value: stats.statusCounts.raw_uploaded ?? 0,
            tone: "info",
            sub: "Awaiting processing",
          },
          {
            label: "Processing",
            value: stats.statusCounts.processing ?? 0,
            tone: "warning",
            sub: "In flight",
          },
          {
            label: "Processed",
            value: stats.statusCounts.processed ?? 0,
            tone: "success",
            sub: `${stats.totalSpeechHours.toFixed(1)}h speech`,
          },
          {
            label: "Clips for review",
            value: stats.clipCounts.pending_review ?? 0,
            tone: "warning",
          },
          {
            label: "Approved",
            value: stats.clipCounts.approved ?? 0,
            tone: "success",
          },
        ]}
      />

      {/* KPI row */}
      <Section
        title="Key metrics"
        description="Totals across the pipeline, updated on page load."
      >
        <div className="grid grid-cols-2 md:grid-cols-4 gap-5">
          <StatCard
            label="Speech hours retained"
            value={stats.totalSpeechHours.toFixed(1)}
            sub="From processed recordings"
            tone="neutral"
          />
          <StatCard
            label="Total clips"
            value={stats.totalClips.toLocaleString()}
            sub={`${(stats.clipCounts.approved ?? 0).toLocaleString()} approved · ${(stats.clipCounts.pending_review ?? 0).toLocaleString()} pending`}
          />
          <StatCard
            label="Real failures"
            value={stats.realFailedCount.toLocaleString()}
            sub={
              stats.archivedCount > 0
                ? `+${stats.archivedCount.toLocaleString()} archived Ateso (excluded)`
                : "No archived set"
            }
            tone="danger"
          />
          <StatCard
            label="In flight"
            value={(stats.statusCounts.processing ?? 0).toLocaleString()}
            sub={`${(stats.statusCounts.raw_uploaded ?? 0).toLocaleString()} queued behind`}
            tone="warning"
          />
        </div>
      </Section>

      {/* Recent activity */}
      <div className="grid lg:grid-cols-2 gap-8">
        <Section
          title="Recently processed"
          description="The eight most recent processed recordings."
        >
          <div className="rounded-2xl bg-surface-lowest overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left bg-surface-low">
                  <th className="px-5 py-3 text-[11px] font-medium text-fg-muted uppercase tracking-[0.08em] font-[family-name:var(--font-body)]">
                    Recording
                  </th>
                  <th className="px-5 py-3 text-[11px] font-medium text-fg-muted uppercase tracking-[0.08em] font-[family-name:var(--font-body)]">
                    Yield
                  </th>
                  <th className="px-5 py-3 text-[11px] font-medium text-fg-muted uppercase tracking-[0.08em] font-[family-name:var(--font-body)]">
                    Clips
                  </th>
                  <th className="px-5 py-3 text-[11px] font-medium text-fg-muted uppercase tracking-[0.08em] font-[family-name:var(--font-body)]">
                    Speech
                  </th>
                </tr>
              </thead>
              <tbody>
                {stats.recentProcessed.length === 0 ? (
                  <tr>
                    <td
                      colSpan={4}
                      className="px-5 py-10 text-center text-sm text-fg-subtle"
                    >
                      No processed recordings yet.
                    </td>
                  </tr>
                ) : (
                  stats.recentProcessed.map((r, i) => (
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
                        <YieldPill value={r.speech_yield ?? 0} />
                      </td>
                      <td className="px-5 py-3 tabular-nums text-fg font-[family-name:var(--font-label)]">
                        {r.clip_count ?? 0}
                      </td>
                      <td className="px-5 py-3 tabular-nums text-fg-muted font-[family-name:var(--font-label)]">
                        {((r.speech_seconds ?? 0) / 60).toFixed(0)}m
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </Section>

        <Section
          title="Recent failures"
          description="Real failures only · archived Ateso excluded."
        >
          <div className="rounded-2xl bg-surface-lowest overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left bg-surface-low">
                  <th className="px-5 py-3 text-[11px] font-medium text-fg-muted uppercase tracking-[0.08em] font-[family-name:var(--font-body)]">
                    Recording
                  </th>
                  <th className="px-5 py-3 text-[11px] font-medium text-fg-muted uppercase tracking-[0.08em] font-[family-name:var(--font-body)]">
                    Reason
                  </th>
                </tr>
              </thead>
              <tbody>
                {stats.recentFailed.length === 0 ? (
                  <tr>
                    <td
                      colSpan={2}
                      className="px-5 py-10 text-center text-sm text-fg-subtle"
                    >
                      No recent failures.
                    </td>
                  </tr>
                ) : (
                  stats.recentFailed.map((r, i) => (
                    <tr
                      key={r.id}
                      className={`transition-colors hover:bg-surface-hover ${
                        i % 2 === 1 ? "bg-surface-low/50" : ""
                      }`}
                    >
                      <td className="px-5 py-3 text-xs text-fg-muted align-top whitespace-nowrap font-[family-name:var(--font-label)]">
                        {r.id.slice(0, 8)}
                      </td>
                      <td className="px-5 py-3 text-xs text-fg-muted leading-relaxed font-[family-name:var(--font-body)]">
                        {r.failure_reason
                          ?.split(":")[0]
                          ?.trim() || "Unknown"}
                        <span className="block mt-0.5 text-fg-subtle truncate max-w-xs">
                          {r.failure_reason?.slice(0, 80)}
                          {(r.failure_reason?.length ?? 0) > 80 ? "..." : ""}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </Section>
      </div>
    </div>
  );
}
