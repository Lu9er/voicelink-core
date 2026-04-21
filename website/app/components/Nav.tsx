"use client";

import Link from "next/link";
import Image from "next/image";
import { useState } from "react";

const links = [
  { href: "/", label: "Home" },
  { href: "/about", label: "About" },
  { href: "/how-it-works", label: "How It Works" },
  { href: "/partners", label: "Partners" },
  { href: "/contact", label: "Contact" },
];

export default function Nav() {
  const [open, setOpen] = useState(false);

  return (
    <nav className="bg-surface-low">
      <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-10 py-4 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-3">
          <Image src="/logo-nav.png" alt="VoiceLink" width={32} height={32} className="h-8 w-8" priority />
        </Link>

        {/* Desktop links */}
        <div className="hidden md:flex items-center gap-8">
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className="text-sm font-medium text-fg-muted hover:text-primary transition-colors font-[family-name:var(--font-body)]"
            >
              {l.label}
            </Link>
          ))}
          <a
            href="https://pipeline.voicelink.cloud"
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm font-semibold text-surface-lowest bg-primary px-5 py-2 rounded-lg hover:opacity-90 transition-opacity font-[family-name:var(--font-body)]"
          >
            Live Dashboard
          </a>
        </div>

        {/* Mobile menu toggle */}
        <button
          onClick={() => setOpen(!open)}
          className="md:hidden p-2 text-fg-muted"
          aria-label="Toggle menu"
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            {open ? (
              <path d="M6 6l12 12M6 18L18 6" />
            ) : (
              <path d="M4 6h16M4 12h16M4 18h16" />
            )}
          </svg>
        </button>
      </div>

      {/* Mobile menu */}
      {open && (
        <div className="md:hidden bg-surface-low px-6 pb-6 space-y-3">
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              onClick={() => setOpen(false)}
              className="block text-sm font-medium text-fg-muted hover:text-primary transition-colors py-2 font-[family-name:var(--font-body)]"
            >
              {l.label}
            </Link>
          ))}
          <a
            href="https://pipeline.voicelink.cloud"
            target="_blank"
            rel="noopener noreferrer"
            className="block text-sm font-semibold text-surface-lowest bg-primary px-5 py-2.5 rounded-lg text-center font-[family-name:var(--font-body)]"
          >
            Live Dashboard
          </a>
        </div>
      )}
    </nav>
  );
}
