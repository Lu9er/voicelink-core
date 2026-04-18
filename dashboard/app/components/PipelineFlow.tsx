type Stage = {
  label: string;
  value: number;
  tone?: "neutral" | "info" | "success" | "warning" | "danger";
  sub?: string;
};

const toneDot: Record<NonNullable<Stage["tone"]>, string> = {
  neutral: "bg-fg-subtle",
  info: "bg-secondary",
  success: "bg-tertiary",
  warning: "bg-warning",
  danger: "bg-danger",
};

export function PipelineFlow({ stages }: { stages: Stage[] }) {
  return (
    <div className="rounded-2xl bg-surface-low p-8">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-sm font-semibold text-primary tracking-tight font-[family-name:var(--font-headline)]">
          Pipeline flow
        </h2>
        <span className="text-[11px] text-fg-subtle uppercase tracking-[0.08em] font-[family-name:var(--font-body)]">
          Live
        </span>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {stages.map((s, i) => (
          <div key={s.label} className="relative">
            <div className="rounded-xl bg-surface-lowest px-5 py-5">
              <div className="flex items-center gap-2">
                <span
                  className={`h-1.5 w-1.5 rounded-full ${
                    toneDot[s.tone ?? "neutral"]
                  }`}
                />
                <p className="text-[11px] font-medium text-fg-muted uppercase tracking-[0.08em] font-[family-name:var(--font-body)]">
                  {s.label}
                </p>
              </div>
              <p className="mt-3 text-2xl font-semibold tabular-nums tracking-tight text-fg font-[family-name:var(--font-label)]">
                {s.value.toLocaleString()}
              </p>
              {s.sub && (
                <p className="mt-1 text-[11px] text-fg-subtle font-[family-name:var(--font-body)]">{s.sub}</p>
              )}
            </div>
            {i < stages.length - 1 && (
              <span
                aria-hidden
                className="hidden md:block absolute top-1/2 -right-2.5 -translate-y-1/2 text-fg-subtle/50 text-sm select-none"
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
