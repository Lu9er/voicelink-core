type Tone = "neutral" | "info" | "success" | "warning" | "danger";

const toneText: Record<Tone, string> = {
  neutral: "text-fg",
  info: "text-secondary",
  success: "text-tertiary",
  warning: "text-warning",
  danger: "text-danger",
};

export function StatCard({
  label,
  value,
  sub,
  tone = "neutral",
  hint,
}: {
  label: string;
  value: string | number;
  sub?: string;
  tone?: Tone;
  hint?: string;
}) {
  return (
    <div className="group rounded-2xl bg-surface-lowest p-8 transition-colors hover:bg-surface-high">
      <div className="flex items-start justify-between">
        <p className="text-[11px] font-medium text-fg-muted uppercase tracking-[0.08em] font-[family-name:var(--font-body)]">
          {label}
        </p>
        {hint && (
          <span className="text-[11px] text-fg-subtle font-[family-name:var(--font-body)]">{hint}</span>
        )}
      </div>
      <p
        className={`mt-4 text-[32px] leading-none font-semibold tabular-nums tracking-tight font-[family-name:var(--font-label)] ${toneText[tone]}`}
      >
        {value}
      </p>
      {sub && (
        <p className="mt-3 text-xs text-fg-subtle leading-relaxed font-[family-name:var(--font-body)]">{sub}</p>
      )}
    </div>
  );
}
