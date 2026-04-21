import Image from "next/image";
import Link from "next/link";

const stats = [
  { value: "512.5", label: "Hours of spontaneous speech collected" },
  { value: "128k+", label: "Speech clips generated" },
  { value: "2", label: "Radio station partners" },
  { value: "27+", label: "Languages spoken across partner regions" },
];

const steps = [
  {
    number: "01",
    title: "Radio Archives",
    description: "Broadcast audio is ingested from partner radio stations with full consent and licensing.",
  },
  {
    number: "02",
    title: "Speech Processing",
    description: "Voice Activity Detection segments continuous audio into clean, individual speech clips.",
  },
  {
    number: "03",
    title: "Review & Preparation",
    description: "Clips are reviewed for quality, annotated with metadata, and prepared for contribution.",
  },
  {
    number: "04",
    title: "Open Datasets",
    description: "Validated speech data is submitted to Mozilla Common Voice and other open repositories.",
  },
];

export default function Home() {
  return (
    <>
      {/* Hero */}
      <section className="bg-surface-low">
        <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-10 py-20 sm:py-28 lg:py-36">
          <div className="max-w-3xl">
            <p className="text-sm font-semibold tracking-widest uppercase text-secondary mb-6 font-[family-name:var(--font-label)]">
              Supported by the Mozilla Common Voice Public API Developer Fund
            </p>
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight text-primary leading-[1.1] font-[family-name:var(--font-headline)]">
              Radio call integration for multilingual speech data collection
            </h1>
            <p className="mt-8 text-lg sm:text-xl text-fg-muted leading-relaxed max-w-2xl font-[family-name:var(--font-body)]">
              A project by Neuravox, supported by the Mozilla Common Voice Public API
              Developer Fund. Uganda&apos;s 300+ radio stations generate thousands of hours of
              natural speech daily across 27+ languages. VoiceLink captures this spontaneous
              speech and channels it into open datasets through a model that benefits stations
              and communities alike.
            </p>
            <div className="mt-10 flex flex-wrap gap-4">
              <Link
                href="/how-it-works"
                className="inline-flex items-center px-7 py-3 text-sm font-semibold text-surface-lowest bg-primary rounded-lg hover:opacity-90 transition-opacity font-[family-name:var(--font-body)]"
              >
                How It Works
              </Link>
              <Link
                href="/progress"
                className="inline-flex items-center px-7 py-3 text-sm font-semibold text-primary bg-primary-soft rounded-lg hover:bg-surface-container transition-colors font-[family-name:var(--font-body)]"
              >
                View Progress
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works Strip */}
      <section className="bg-bg">
        <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-10 py-20 sm:py-24">
          <h2 className="text-2xl sm:text-3xl font-bold text-primary mb-4 font-[family-name:var(--font-headline)]">
            How it works
          </h2>
          <p className="text-fg-muted mb-12 max-w-2xl font-[family-name:var(--font-body)]">
            From radio broadcast to open speech dataset in four stages.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {steps.map((step) => (
              <div
                key={step.number}
                className="bg-surface-low rounded-2xl p-8 hover:bg-surface-container transition-colors"
              >
                <span className="text-3xl font-bold text-secondary font-[family-name:var(--font-label)]">
                  {step.number}
                </span>
                <h3 className="mt-4 text-lg font-semibold text-fg font-[family-name:var(--font-headline)]">
                  {step.title}
                </h3>
                <p className="mt-3 text-sm text-fg-muted leading-relaxed font-[family-name:var(--font-body)]">
                  {step.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="bg-surface-low">
        <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-10 py-20 sm:py-24">
          <h2 className="text-2xl sm:text-3xl font-bold text-primary mb-12 font-[family-name:var(--font-headline)]">
            Progress to date
          </h2>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-6 sm:gap-8">
            {stats.map((stat) => (
              <div key={stat.label}>
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

      {/* Partners */}
      <section className="bg-bg">
        <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-10 py-20 sm:py-24">
          <h2 className="text-2xl sm:text-3xl font-bold text-primary mb-4 font-[family-name:var(--font-headline)]">
            Our funder and partners
          </h2>
          <p className="text-fg-muted mb-12 max-w-2xl font-[family-name:var(--font-body)]">
            VoiceLink is supported by the Mozilla Foundation and works directly with established
            radio stations who serve their language communities.
          </p>
          <div className="flex flex-wrap items-center gap-8 sm:gap-12">
            <div className="bg-surface-low rounded-2xl p-8 flex items-center justify-center w-48 h-28">
              <Image
                src="/mozilla-logo.png"
                alt="Mozilla Foundation"
                width={160}
                height={60}
                className="object-contain max-h-16"
              />
            </div>
            <div className="bg-surface-low rounded-2xl p-8 flex items-center justify-center w-48 h-28">
              <Image
                src="/cbs-logo.png"
                alt="CBS Radio 88.8 FM"
                width={160}
                height={60}
                className="object-contain max-h-16"
              />
            </div>
            <div className="bg-surface-low rounded-2xl p-8 flex items-center justify-center w-48 h-28">
              <Image
                src="/vot-logo.webp"
                alt="Voice of Teso 88.4 FM"
                width={160}
                height={60}
                className="object-contain max-h-16"
              />
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="bg-surface-low">
        <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-10 py-20 sm:py-24 text-center">
          <h2 className="text-2xl sm:text-3xl font-bold text-primary mb-6 font-[family-name:var(--font-headline)]">
            Interested in partnering?
          </h2>
          <p className="text-fg-muted mb-8 max-w-xl mx-auto font-[family-name:var(--font-body)]">
            We work with radio stations, language communities, researchers, and funders
            committed to linguistic inclusion in technology.
          </p>
          <Link
            href="/contact"
            className="inline-flex items-center px-7 py-3 text-sm font-semibold text-surface-lowest bg-primary rounded-lg hover:opacity-90 transition-opacity font-[family-name:var(--font-body)]"
          >
            Get in Touch
          </Link>
        </div>
      </section>
    </>
  );
}
