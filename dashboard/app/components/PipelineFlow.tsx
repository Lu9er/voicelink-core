type Stage = {
  label: string;
  value: number;
  tone?: "neutral" | "info" | "success" | "warning" | "danger";
  sub?: string;
};

const toneDot: Record<NonNullable<Stage["tone"]>, string> = {
  neutral: "bg-fg-subtle",
  info: "bg-info",
  success: "bg-success",
  warning: "bg-warning",
  danger: "bg-danger",
};

export function PipelineFlow({ stages }: { stages: Stage[] }) {
  return (
    <div className="rounded-xl border border-border bg-surface p-5">
      <div className="flex items-center justify-between mb-5">
        <h2 className="text-sm font-semibold text-fg tracking-tight">
          Pipeline flow
        </h2>
        <span className="text-[11px] text-fg-subtle uppercase tracking-[0.08em]">
          Live
        </span>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {stages.map((s, i) => (
          <div key={s.label} className="relative">
            <div className="rounded-lg border border-border bg-surface-elev px-4 py-3.5">
              <div className="flex items-center gap-2">
                <span
                  className={`h-1.5 w-1.5 rounded-full ${
                    toneDot[s.tone ?? "neutral"]
                  }`}
                />
                <p className="text-[11px] font-medium text-fg-muted uppercase tracking-[0.08em]">
                  {s.label}
                </p>
              </div>
              <p className="mt-2 text-xl font-semibold tabular-nums tracking-tight text-fg">
                {s.value.toLocaleString()}
              </p>
              {s.sub && (
                <p className="mt-0.5 text-[11px] text-fg-subtle">{s.sub}</p>
              )}
            </div>
            {i < stages.length - 1 && (
              <span
                aria-hidden
                className="hidden md:block absolute top-1/2 -right-2 -translate-y-1/2 text-fg-subtle text-sm select-none"
              >
                →
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
