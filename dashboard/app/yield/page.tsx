import { supabase } from "@/lib/supabase";
import { StatCard } from "../components/StatCard";
import { Section } from "../components/Section";

export const dynamic = "force-dynamic";

async function getYieldStats() {
  const { data: processed } = await supabase
    .from("recordings")
    .select("id, speech_yield, clip_count, speech_seconds, duration_seconds")
    .eq("status", "processed");

  const rows = processed ?? [];
  if (rows.length === 0) return null;

  const yields = rows
    .map((r) => r.speech_yield ?? 0)
    .sort((a, b) => a - b);

  const avgYield = yields.reduce((a, b) => a + b, 0) / yields.length;
  const medianYield = yields[Math.floor(yields.length / 2)];

  const high = yields.filter((y) => y > 0.5).length;
  const medium = yields.filter((y) => y >= 0.2 && y <= 0.5).length;
  const low = yields.filter((y) => y < 0.2).length;

  const totalClips = rows.reduce((s, r) => s + (r.clip_count ?? 0), 0);
  const totalSpeech = rows.reduce((s, r) => s + (r.speech_seconds ?? 0), 0);
  const totalInput = rows.reduce(
    (s, r) => s + (r.duration_seconds ?? 0),
    0,
  );
  const avgClipsPerFile = totalClips / rows.length;

  const clipDurations = rows
    .filter((r) => r.clip_count && r.speech_seconds)
    .map((r) => (r.speech_seconds ?? 0) / (r.clip_count ?? 1));
  const avgClipLength =
    clipDurations.length > 0
      ? clipDurations.reduce((a, b) => a + b, 0) / clipDurations.length
      : 0;

  const sorted = [...rows].sort(
    (a, b) => (b.speech_yield ?? 0) - (a.speech_yield ?? 0),
  );
  const top10 = sorted.slice(0, 10);
  const bottom10 = sorted.slice(-10).reverse();

  const buckets = Array.from({ length: 10 }, (_, i) => ({
    label: `${i * 10}-${(i + 1) * 10}%`,
    count: yields.filter((y) => y >= i * 0.1 && y < (i + 1) * 0.1).length,
  }));
  buckets[9].count += yields.filter((y) => y >= 1.0).length;

  return {
    count: rows.length,
    avgYield,
    medianYield,
    high,
    medium,
    low,
    totalClips,
    totalSpeechHours: totalSpeech / 3600,
    totalInputHours: totalInput / 3600,
    avgClipsPerFile,
    avgClipLength,
    top10,
    bottom10,
    buckets,
  };
}

function Histogram({
  buckets,
}: {
  buckets: { label: string; count: number }[];
}) {
  const max = Math.max(...buckets.map((b) => b.count), 1);
  const trackHeight = 192; // px

  return (
    <div className="space-y-4">
      <div className="flex items-end gap-3 px-1" style={{ height: trackHeight }}>
        {buckets.map((b) => {
          const ratio = b.count / max;
          const barPx = b.count > 0 ? Math.max(Math.round(ratio * trackHeight), 6) : 0;
          return (
            <div
              key={b.label}
              className="flex-1 flex flex-col items-center justify-end"
              style={{ height: trackHeight }}
            >
              <span className="text-[11px] tabular-nums text-fg-muted mb-1.5 font-[family-name:var(--font-label)]">
                {b.count}
              </span>
              <div
                className="w-full rounded-t-lg"
                style={{
                  height: barPx,
                  backgroundColor: "var(--secondary)",
                }}
              />
            </div>
          );
        })}
      </div>
      <div className="flex gap-3 px-1">
        {buckets.map((b) => (
          <div key={b.label} className="flex-1 text-center">
            <p className="text-[10px] text-fg-subtle font-[family-name:var(--font-label)]">{b.label}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

export default async function YieldPage() {
  const stats = await getYieldStats();

  if (!stats) {
    return (
      <div className="space-y-4">
        <h1 className="text-[36px] leading-tight font-bold tracking-tight text-primary font-[family-name:var(--font-headline)]">
          Yield analytics
        </h1>
        <p className="text-sm text-fg-muted font-[family-name:var(--font-body)]">
          No processed recordings yet.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-12">
      {/* Hero */}
      <div>
        <p className="text-xs font-medium text-secondary uppercase tracking-[0.12em] font-[family-name:var(--font-body)]">
          Quality
        </p>
        <h1 className="mt-3 text-[36px] leading-tight font-bold tracking-tight text-primary font-[family-name:var(--font-headline)]">
          Yield analytics
        </h1>
        <p className="mt-2 text-sm text-fg-muted max-w-2xl font-[family-name:var(--font-body)]">
          How much usable speech we retain from each recording after
          voice-activity detection and filtering.
        </p>
      </div>

      {/* Primary stats */}
      <Section title="Headline" description="Based on processed recordings only.">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-5">
          <StatCard
            label="Files processed"
            value={stats.count.toLocaleString()}
          />
          <StatCard
            label="Avg yield"
            value={`${(stats.avgYield * 100).toFixed(1)}%`}
            tone="info"
          />
          <StatCard
            label="Median yield"
            value={`${(stats.medianYield * 100).toFixed(1)}%`}
            tone="info"
          />
          <StatCard
            label="Speech hours"
            value={stats.totalSpeechHours.toFixed(1)}
            sub={`from ${stats.totalInputHours.toFixed(1)}h input`}
            tone="success"
          />
        </div>
      </Section>

      {/* Secondary stats */}
      <Section title="Clip geometry">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-5">
          <StatCard
            label="Total clips"
            value={stats.totalClips.toLocaleString()}
          />
          <StatCard
            label="Avg clips per file"
            value={stats.avgClipsPerFile.toFixed(0)}
          />
          <StatCard
            label="Avg clip length"
            value={`${stats.avgClipLength.toFixed(1)}s`}
          />
          <div className="rounded-2xl bg-surface-lowest p-8">
            <p className="text-[11px] font-medium text-fg-muted uppercase tracking-[0.08em] font-[family-name:var(--font-body)]">
              Yield bands
            </p>
            <div className="mt-4 space-y-2.5">
              <div className="flex items-center justify-between text-xs">
                <span className="flex items-center gap-2 text-fg font-[family-name:var(--font-body)]">
                  <span className="h-2 w-2 rounded-full bg-tertiary" />
                  High (&gt;50%)
                </span>
                <span className="tabular-nums text-fg-muted font-[family-name:var(--font-label)]">
                  {stats.high}
                </span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="flex items-center gap-2 text-fg font-[family-name:var(--font-body)]">
                  <span className="h-2 w-2 rounded-full bg-warning" />
                  Mid (20-50%)
                </span>
                <span className="tabular-nums text-fg-muted font-[family-name:var(--font-label)]">
                  {stats.medium}
                </span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="flex items-center gap-2 text-fg font-[family-name:var(--font-body)]">
                  <span className="h-2 w-2 rounded-full bg-danger" />
                  Low (&lt;20%)
                </span>
                <span className="tabular-nums text-fg-muted font-[family-name:var(--font-label)]">
                  {stats.low}
                </span>
              </div>
            </div>
          </div>
        </div>
      </Section>

      {/* Distribution */}
      <Section
        title="Yield distribution"
        description="How files are distributed across yield buckets."
      >
        <div className="rounded-2xl bg-surface-lowest p-8">
          <Histogram buckets={stats.buckets} />
        </div>
      </Section>

      {/* Top and bottom */}
      <div className="grid md:grid-cols-2 gap-8">
        <Section title="Top 10 by yield">
          <div className="rounded-2xl bg-surface-lowest overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left bg-surface-low">
                  <th className="px-5 py-3 text-[11px] font-medium text-fg-muted uppercase tracking-[0.08em] font-[family-name:var(--font-body)]">
                    ID
                  </th>
                  <th className="px-5 py-3 text-[11px] font-medium text-fg-muted uppercase tracking-[0.08em] font-[family-name:var(--font-body)]">
                    Yield
                  </th>
                  <th className="px-5 py-3 text-[11px] font-medium text-fg-muted uppercase tracking-[0.08em] font-[family-name:var(--font-body)]">
                    Clips
                  </th>
                </tr>
              </thead>
              <tbody>
                {stats.top10.map((r, i) => (
                  <tr
                    key={r.id}
                    className={`transition-colors hover:bg-surface-hover ${
                      i % 2 === 1 ? "bg-surface-low/50" : ""
                    }`}
                  >
                    <td className="px-5 py-3 text-xs text-fg-muted font-[family-name:var(--font-label)]">
                      {r.id.slice(0, 8)}
                    </td>
                    <td className="px-5 py-3 tabular-nums text-tertiary font-[family-name:var(--font-label)]">
                      {((r.speech_yield ?? 0) * 100).toFixed(1)}%
                    </td>
                    <td className="px-5 py-3 tabular-nums text-fg font-[family-name:var(--font-label)]">
                      {r.clip_count}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>

        <Section title="Bottom 10 by yield">
          <div className="rounded-2xl bg-surface-lowest overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left bg-surface-low">
                  <th className="px-5 py-3 text-[11px] font-medium text-fg-muted uppercase tracking-[0.08em] font-[family-name:var(--font-body)]">
                    ID
                  </th>
                  <th className="px-5 py-3 text-[11px] font-medium text-fg-muted uppercase tracking-[0.08em] font-[family-name:var(--font-body)]">
                    Yield
                  </th>
                  <th className="px-5 py-3 text-[11px] font-medium text-fg-muted uppercase tracking-[0.08em] font-[family-name:var(--font-body)]">
                    Clips
                  </th>
                </tr>
              </thead>
              <tbody>
                {stats.bottom10.map((r, i) => (
                  <tr
                    key={r.id}
                    className={`transition-colors hover:bg-surface-hover ${
                      i % 2 === 1 ? "bg-surface-low/50" : ""
                    }`}
                  >
                    <td className="px-5 py-3 text-xs text-fg-muted font-[family-name:var(--font-label)]">
                      {r.id.slice(0, 8)}
                    </td>
                    <td className="px-5 py-3 tabular-nums text-danger font-[family-name:var(--font-label)]">
                      {((r.speech_yield ?? 0) * 100).toFixed(1)}%
                    </td>
                    <td className="px-5 py-3 tabular-nums text-fg font-[family-name:var(--font-label)]">
                      {r.clip_count}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>
      </div>
    </div>
  );
}
