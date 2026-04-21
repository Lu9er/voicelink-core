"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";

const items = [
  { href: "/", label: "Overview" },
  { href: "/recordings", label: "Recordings" },
  { href: "/live", label: "Live" },
  { href: "/yield", label: "Yield" },
  { href: "/clips", label: "Clips" },
];

export default function Nav() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-10 bg-surface-lowest/80 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-10">
        <div className="flex items-center h-16 gap-10">
          <Link href="/" className="flex items-center gap-3">
            <Image
              src="/logo-nav.png"
              alt="VoiceLink"
              width={30}
              height={30}
              className="rounded-lg"
            />
            <div className="flex items-baseline gap-2">
              <span className="text-[15px] font-semibold text-primary font-[family-name:var(--font-headline)] tracking-tight">
                VoiceLink
              </span>
              <span className="hidden sm:inline text-xs text-fg-subtle font-[family-name:var(--font-body)]">
                Data Ingestion Pipeline
              </span>
            </div>
          </Link>

          <nav className="flex items-center h-full gap-1">
            {items.map(({ href, label }) => {
              const active =
                href === "/" ? pathname === "/" : pathname.startsWith(href);
              return (
                <Link
                  key={href}
                  href={href}
                  className={`relative inline-flex items-center h-full px-4 text-sm font-[family-name:var(--font-body)] transition-colors ${
                    active
                      ? "text-primary font-medium"
                      : "text-fg-muted hover:text-fg"
                  }`}
                >
                  {label}
                  {active && (
                    <span className="absolute left-4 right-4 -bottom-px h-[2px] bg-secondary rounded-full" />
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
