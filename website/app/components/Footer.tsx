import Link from "next/link";

export default function Footer() {
  return (
    <footer className="bg-surface-low">
      <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-10 py-10">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-8 mb-10">
          <div>
            <p className="text-sm font-semibold text-fg mb-3 font-[family-name:var(--font-headline)]">
              VoiceLink
            </p>
            <p className="text-sm text-fg-muted leading-relaxed font-[family-name:var(--font-body)]">
              Speech data infrastructure for underrepresented African languages.
            </p>
          </div>
          <div>
            <p className="text-sm font-semibold text-fg mb-3 font-[family-name:var(--font-headline)]">
              Pages
            </p>
            <div className="space-y-2">
              {[
                { href: "/about", label: "About" },
                { href: "/how-it-works", label: "How It Works" },
                { href: "/partners", label: "Partners" },
                { href: "/contact", label: "Contact" },
              ].map((l) => (
                <Link
                  key={l.href}
                  href={l.href}
                  className="block text-sm text-fg-muted hover:text-primary transition-colors font-[family-name:var(--font-body)]"
                >
                  {l.label}
                </Link>
              ))}
            </div>
          </div>
          <div>
            <p className="text-sm font-semibold text-fg mb-3 font-[family-name:var(--font-headline)]">
              Resources
            </p>
            <div className="space-y-2">
              <a
                href="https://pipeline.voicelink.cloud"
                target="_blank"
                rel="noopener noreferrer"
                className="block text-sm text-fg-muted hover:text-primary transition-colors font-[family-name:var(--font-body)]"
              >
                Live Dashboard
              </a>
              <a
                href="https://commonvoice.mozilla.org"
                target="_blank"
                rel="noopener noreferrer"
                className="block text-sm text-fg-muted hover:text-primary transition-colors font-[family-name:var(--font-body)]"
              >
                Mozilla Common Voice
              </a>
              <a
                href="https://neuravox.org"
                target="_blank"
                rel="noopener noreferrer"
                className="block text-sm text-fg-muted hover:text-primary transition-colors font-[family-name:var(--font-body)]"
              >
                Neuravox
              </a>
            </div>
          </div>
        </div>
        <div className="pt-6 flex flex-col sm:flex-row gap-2 sm:gap-4 items-start sm:items-center justify-between"
          style={{ borderTop: "1px solid var(--border)" }}>
          <p className="text-xs text-fg-subtle font-[family-name:var(--font-body)]">
            A{" "}
            <a
              href="https://neuravox.org"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-primary transition-colors"
            >
              Neuravox
            </a>{" "}
            project
          </p>
          <p className="text-[11px] text-fg-subtle tracking-wide font-[family-name:var(--font-body)]">
            Theme follows your system preference
          </p>
        </div>
      </div>
    </footer>
  );
}
