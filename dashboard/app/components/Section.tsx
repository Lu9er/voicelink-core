import { ReactNode } from "react";

export function Section({
  title,
  description,
  action,
  children,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="space-y-3">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h2 className="text-[13px] font-semibold text-fg tracking-tight">
            {title}
          </h2>
          {description && (
            <p className="mt-0.5 text-xs text-fg-subtle">{description}</p>
          )}
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}
