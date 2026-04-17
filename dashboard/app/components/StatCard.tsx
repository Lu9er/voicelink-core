type Tone = "neutral" | "info" | "success" | "warning" | "danger";

const toneText: Record<Tone, string> = {
  neutral: "text-fg",
  info: "text-info",
  success: "text-success",
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
    <div className="group rounded-xl border border-border bg-surface p-5 transition-colors hover:border-border-strong">
      <div className="flex items-start justify-between">
        <p className="text-[11px] font-medium text-fg-muted uppercase tracking-[0.08em]">
          {label}
        </p>
        {hint && (
          <span className="text-[11px] text-fg-subtle">{hint}</span>
        )}
      </div>
      <p
        className={`mt-3 text-[28px] leading-none font-semibold tabular-nums tracking-tight ${toneText[tone]}`}
      >
        {value}
      </p>
      {sub && (
        <p className="mt-2 text-xs text-fg-subtle leading-relaxed">{sub}</p>
      )}
    </div>
  );
}
