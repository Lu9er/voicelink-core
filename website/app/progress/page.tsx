import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Progress - VoiceLink",
  description:
    "Milestones and progress updates from the VoiceLink speech data infrastructure project.",
};

const milestones = [
  {
    date: "April 2026",
    title: "500-hour speech target achieved",
    description:
      "Processed over 512 hours of retained Luganda speech from CBS Radio archives, generating more than 128,000 individual speech clips. Aggregate speech yield of 68.4% across the processed corpus.",
  },
  {
    date: "April 2026",
    title: "Pipeline dashboard deployed",
    description:
      "Launched an internal operations dashboard for real-time monitoring of the data processing pipeline, tracking recordings, clips, yield analytics, and processing status.",
  },
  {
    date: "April 2026",
    title: "Voice of Teso partnership confirmed",
    description:
      "Secured partnership with Voice of Teso 88.4 FM in Soroti for Ateso language data collection, extending the pipeline to a second language and station.",
  },
  {
    date: "February 2026",
    title: "CBS Radio archive ingestion completed",
    description:
      "Ingested approximately 1,900 one-hour broadcast recordings from the CBS Radio 88.8 FM archives into cloud storage with full deduplication and metadata tracking.",
  },
  {
    date: "February 2026",
    title: "Audio processing pipeline built",
    description:
      "Completed the end-to-end processing pipeline: archive ingestion, voice activity detection, speech segmentation, clip generation, and quality gating. Validated with initial yield tests showing strong speech retention.",
  },
  {
    date: "December 2025",
    title: "CBS Radio partnership signed",
    description:
      "Signed partnership agreement with CBS Radio 88.8 FM, Uganda's largest cultural radio institution, for access to broadcast archives and live call-in audio in Luganda.",
  },
  {
    date: "December 2025",
    title: "Project initiated",
    description:
      "VoiceLink Uganda launched with support from the Mozilla Common Voice Public API Developer Fund. Technical planning, Common Voice API integration, and initial station outreach completed.",
  },
];

export default function ProgressPage() {
  return (
    <>
      {/* Header */}
      <section className="bg-surface-low">
        <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-10 py-20 sm:py-28">
          <p className="text-sm font-semibold tracking-widest uppercase text-secondary mb-6 font-[family-name:var(--font-label)]">
            Project Updates
          </p>
          <h1 className="text-4xl sm:text-5xl font-bold tracking-tight text-primary leading-[1.1] max-w-3xl font-[family-name:var(--font-headline)]">
            Progress
          </h1>
          <p className="mt-8 text-lg text-fg-muted max-w-2xl leading-relaxed font-[family-name:var(--font-body)]">
            Key milestones from the VoiceLink project, from inception through to
            current operations.
          </p>
        </div>
      </section>

      {/* Key metrics */}
      <section className="bg-bg">
        <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-10 py-20 sm:py-24">
          <h2 className="text-2xl sm:text-3xl font-bold text-primary mb-12 font-[family-name:var(--font-headline)]">
            Current numbers
          </h2>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-6 sm:gap-8">
            {[
              { value: "512+", label: "Hours of speech retained" },
              { value: "128k+", label: "Speech clips generated" },
              { value: "68%", label: "Average speech yield" },
              { value: "2", label: "Radio station partners" },
            ].map((stat) => (
              <div key={stat.label} className="bg-surface-low rounded-2xl p-8">
                <p className="text-4xl sm:text-5xl font-bold text-secondary font-[family-name:var(--font-label)]">
                  {stat.value}
                </p>
                <p className="mt-3 text-sm text-fg-muted font-[family-name:var(--font-body)]">
                  {stat.label}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Timeline */}
      <section className="bg-surface-low">
        <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-10 py-20 sm:py-24">
          <h2 className="text-2xl sm:text-3xl font-bold text-primary mb-12 font-[family-name:var(--font-headline)]">
            Milestones
          </h2>
          <div className="max-w-3xl space-y-0">
            {milestones.map((m, i) => (
              <div key={i} className="relative pl-10 pb-12 last:pb-0">
                {/* Vertical line */}
                {i < milestones.length - 1 && (
                  <div className="absolute left-[11px] top-3 bottom-0 w-px bg-secondary/20" />
                )}
                {/* Dot */}
                <div className="absolute left-0 top-1.5 h-6 w-6 rounded-full bg-secondary/10 flex items-center justify-center">
                  <div className="h-2.5 w-2.5 rounded-full bg-secondary" />
                </div>
                {/* Content */}
                <p className="text-xs font-semibold text-secondary uppercase tracking-wider mb-2 font-[family-name:var(--font-label)]">
                  {m.date}
                </p>
                <h3 className="text-lg font-semibold text-fg mb-2 font-[family-name:var(--font-headline)]">
                  {m.title}
                </h3>
                <p className="text-sm text-fg-muted leading-relaxed font-[family-name:var(--font-body)]">
                  {m.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}
