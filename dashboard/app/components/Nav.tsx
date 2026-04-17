"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const items = [
  { href: "/", label: "Overview" },
  { href: "/recordings", label: "Recordings" },
  { href: "/yield", label: "Yield" },
  { href: "/clips", label: "Clips" },
];

export default function Nav() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-10 border-b border-border bg-bg/80 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center h-14 gap-8">
          <Link href="/" className="flex items-center gap-2.5">
            <span className="grid place-items-center h-7 w-7 rounded-lg bg-fg text-bg text-[11px] font-semibold tracking-tight">
              VL
            </span>
            <span className="text-[15px] font-semibold text-fg tracking-tight">
              VoiceLink
            </span>
            <span className="hidden sm:inline text-xs text-fg-subtle border-l border-border pl-3 ml-1">
              Ingestion Pipeline
            </span>
          </Link>

          <nav className="flex items-center h-full">
            {items.map(({ href, label }) => {
              const active =
                href === "/" ? pathname === "/" : pathname.startsWith(href);
              return (
                <Link
                  key={href}
                  href={href}
                  className={`relative inline-flex items-center h-full px-3 text-sm transition-colors ${
                    active
                      ? "text-fg"
                      : "text-fg-muted hover:text-fg"
                  }`}
                >
                  {label}
                  {active && (
                    <span className="absolute left-3 right-3 -bottom-px h-[2px] bg-fg rounded-full" />
                  )}
                </Link>
              );
            })}
          </nav>
        </div>
      </div>
    </header>
  );
}
