const map: Record<
  string,
  { label: string; className: string }
> = {
  raw_uploaded: {
    label: "Uploaded",
    className: "bg-info-soft text-secondary",
  },
  processing: {
    label: "Processing",
    className: "bg-warning-soft text-warning",
  },
  processed: {
    label: "Processed",
    className: "bg-success-soft text-tertiary",
  },
  failed: {
    label: "Failed",
    className: "bg-danger-soft text-danger",
  },
  pending_review: {
    label: "Pending review",
    className: "bg-warning-soft text-warning",
  },
  approved: {
    label: "Approved",
    className: "bg-success-soft text-tertiary",
  },
  rejected: {
    label: "Rejected",
    className: "bg-danger-soft text-danger",
  },
};

export function StatusBadge({ status }: { status: string }) {
  const s = map[status] ?? {
    label: status.replace("_", " "),
    className: "bg-surface-elev text-fg-muted",
  };
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11px] font-medium font-[family-name:var(--font-body)] ${s.className}`}
    >
      <span className="h-1 w-1 rounded-full bg-current opacity-80" />
      {s.label}
    </span>
  );
}
