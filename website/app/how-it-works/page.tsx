import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "How It Works - VoiceLink",
  description:
    "From radio archive to open speech dataset: how VoiceLink processes broadcast audio into structured speech data.",
};

const stages = [
  {
    number: "01",
    title: "Radio & Audio Ingestion",
    subtitle: "Archive to pipeline",
    description:
      "Broadcast recordings are transferred from partner radio stations and ingested into the VoiceLink pipeline. Each recording is catalogued with source metadata -- station, programme, date, language -- and stored securely for processing.",
    details: [
      "Bulk archive transfer from station storage systems",
      "Automated file cataloguing and metadata extraction",
      "Support for common broadcast formats (MP3, WAV, FLAC)",
      "Full provenance tracking from source to dataset",
    ],
  },
  {
    number: "02",
    title: "Speech Processing",
    subtitle: "Audio to clips",
    description:
      "Voice Activity Detection (VAD) analyses each recording to identify segments containing speech, separating spoken content from music, silence, and background noise. Each speech segment is extracted as an individual clip.",
    details: [
      "Silero VAD for accurate speech boundary detection",
      "Configurable parameters for segment length and padding",
      "Automatic filtering of non-speech audio",
      "Batch processing of entire archive collections",
    ],
  },
  {
    number: "03",
    title: "Review & Preparation",
    subtitle: "Quality assurance",
    description:
      "Generated clips pass through a review stage where they are assessed for audio quality, speech clarity, and suitability for inclusion in speech datasets. Metadata is verified and clips are formatted to dataset specifications.",
    details: [
      "Human review interface for clip validation",
      "Quality scoring for audio clarity and completeness",
      "Metadata verification and annotation",
      "Format standardisation for target dataset requirements",
    ],
  },
  {
    number: "04",
    title: "Analytics & Insights",
    subtitle: "Monitoring and contribution",
    description:
      "A live operations dashboard tracks every stage of the pipeline -- from ingestion volumes to clip generation rates to submission status. Validated clips are submitted to Mozilla Common Voice and other open speech repositories.",
    details: [
      "Real-time pipeline monitoring at pipeline.voicelink.cloud",
      "Processing statistics and yield analysis",
      "Automated submission to Mozilla Common Voice",
      "Transparent reporting on data provenance",
    ],
  },
];

export default function HowItWorksPage() {
  return (
    <>
      {/* Header */}
      <section className="bg-surface-low">
        <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-10 py-20 sm:py-28">
          <p className="text-sm font-semibold tracking-widest uppercase text-secondary mb-6 font-[family-name:var(--font-label)]">
            Pipeline Architecture
          </p>
          <h1 className="text-4xl sm:text-5xl font-bold tracking-tight text-primary leading-[1.1] max-w-3xl font-[family-name:var(--font-headline)]">
            From radio broadcast to open dataset
          </h1>
          <p className="mt-8 text-lg text-fg-muted max-w-2xl leading-relaxed font-[family-name:var(--font-body)]">
            VoiceLink operates a four-stage pipeline that transforms raw broadcast audio into
            structured, validated speech data ready for contribution to open repositories.
          </p>
        </div>
      </section>

      {/* Stages */}
      {stages.map((stage, i) => (
        <section
          key={stage.number}
          className={i % 2 === 0 ? "bg-bg" : "bg-surface-low"}
        >
          <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-10 py-20 sm:py-24">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-16 items-start">
              <div className="lg:col-span-5">
                <span className="text-5xl sm:text-6xl font-bold text-secondary/30 font-[family-name:var(--font-label)]">
                  {stage.number}
                </span>
                <h2 className="mt-2 text-2xl sm:text-3xl font-bold text-primary font-[family-name:var(--font-headline)]">
                  {stage.title}
                </h2>
                <p className="mt-2 text-sm font-medium text-secondary uppercase tracking-wide font-[family-name:var(--font-label)]">
                  {stage.subtitle}
                </p>
              </div>
              <div className="lg:col-span-7">
                <p className="text-fg-muted leading-relaxed mb-8 font-[family-name:var(--font-body)]">
                  {stage.description}
                </p>
                <ul className="space-y-3">
                  {stage.details.map((detail) => (
                    <li
                      key={detail}
                      className="flex items-start gap-3 text-sm text-fg-muted font-[family-name:var(--font-body)]"
                    >
                      <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-secondary shrink-0" />
                      {detail}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </section>
      ))}

      {/* Dashboard CTA */}
      <section className="bg-surface-low">
        <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-10 py-20 sm:py-24 text-center">
          <h2 className="text-2xl sm:text-3xl font-bold text-primary mb-6 font-[family-name:var(--font-headline)]">
            See the pipeline in action
          </h2>
          <p className="text-fg-muted mb-8 max-w-xl mx-auto font-[family-name:var(--font-body)]">
            The VoiceLink operations dashboard provides real-time visibility into pipeline
            processing across all partner stations and languages.
          </p>
          <a
            href="https://pipeline.voicelink.cloud"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center px-7 py-3 text-sm font-semibold text-surface-lowest bg-primary rounded-lg hover:opacity-90 transition-opacity font-[family-name:var(--font-body)]"
          >
            View Live Dashboard
          </a>
        </div>
      </section>
    </>
  );
}
