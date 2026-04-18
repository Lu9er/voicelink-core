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
    <section className="space-y-5">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h2 className="text-base font-semibold text-primary tracking-tight font-[family-name:var(--font-headline)]">
            {title}
          </h2>
          {description && (
            <p className="mt-1 text-sm text-fg-subtle font-[family-name:var(--font-body)]">{description}</p>
          )}
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}
