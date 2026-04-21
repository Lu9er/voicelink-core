import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "About — VoiceLink",
  description:
    "VoiceLink addresses the critical shortage of speech data for African languages by partnering with radio stations to build open datasets.",
};

export default function AboutPage() {
  return (
    <>
      {/* Header */}
      <section className="bg-surface-low">
        <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-10 py-20 sm:py-28">
          <p className="text-sm font-semibold tracking-widest uppercase text-secondary mb-6 font-[family-name:var(--font-label)]">
            About VoiceLink
          </p>
          <h1 className="text-4xl sm:text-5xl font-bold tracking-tight text-primary leading-[1.1] max-w-3xl font-[family-name:var(--font-headline)]">
            Radio call integration for multilingual speech data collection
          </h1>
          <p className="mt-8 text-lg text-fg-muted max-w-2xl leading-relaxed font-[family-name:var(--font-body)]">
            A project by Neuravox, supported by the Mozilla Common Voice Public API Developer Fund.
          </p>
        </div>
      </section>

      {/* Problem */}
      <section className="bg-bg">
        <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-10 py-20 sm:py-24">
          <div className="max-w-3xl">
            <div className="space-y-5 text-fg-muted leading-relaxed font-[family-name:var(--font-body)]">
              <p>
                African languages are severely underrepresented in AI development. Uganda alone
                is home to 40+ indigenous languages -- Luganda (22.2%), Runyankole (13.4%), and
                Ateso (12.1%) among them -- yet almost none have the speech data needed to build
                working voice technology. The result is a compounding exclusion: languages without
                data do not get technology, and languages without technology lose ground in
                education, governance, and commerce.
              </p>
              <p>
                Yet Uganda&apos;s radio infrastructure generates thousands of hours of natural
                speech daily across 27+ languages from 300+ stations. Radio call-in programmes
                are an untapped source of spontaneous speech -- rich with code-switching, cultural
                context, and natural conversation dynamics that scripted recordings miss.
                A different approach is needed, and the resource already exists.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Approach */}
      <section className="bg-surface-low">
        <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-10 py-20 sm:py-24">
          <div className="max-w-3xl">
            <h2 className="text-2xl sm:text-3xl font-bold text-primary mb-6 font-[family-name:var(--font-headline)]">
              Our approach
            </h2>
            <div className="space-y-5 text-fg-muted leading-relaxed font-[family-name:var(--font-body)]">
              <p>
                VoiceLink integrates with radio station infrastructure to capture natural
                speech for open datasets like Mozilla Common Voice, while providing stations
                with operational tools and insights -- a value exchange model where both
                parties benefit.
              </p>
              <p>
                We build automated pipelines that ingest broadcast audio, segment it into individual
                speech clips using Voice Activity Detection, and prepare it for contribution to
                open speech datasets like Mozilla Common Voice. Every partnership is built on
                informed consent, licensing agreements, and respect for the communities whose voices
                make this work possible.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Why Radio */}
      <section className="bg-bg">
        <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-10 py-20 sm:py-24">
          <div className="max-w-3xl">
            <h2 className="text-2xl sm:text-3xl font-bold text-primary mb-6 font-[family-name:var(--font-headline)]">
              Why radio
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 mt-8">
              {[
                {
                  title: "Scale",
                  text: "A single station may hold 10,000+ hours of recordings spanning decades of broadcast.",
                },
                {
                  title: "Spontaneous speech",
                  text: "Radio call-ins capture how people actually speak -- with code-switching, natural prosody, cultural context, and conversational dynamics that scripted recordings miss.",
                },
                {
                  title: "Language coverage",
                  text: "Africa has hundreds of community radio stations broadcasting in local languages daily.",
                },
                {
                  title: "Institutional trust",
                  text: "Radio stations are established community institutions with existing relationships and governance.",
                },
              ].map((item) => (
                <div
                  key={item.title}
                  className="bg-surface-low rounded-2xl p-8"
                >
                  <h3 className="text-lg font-semibold text-fg mb-3 font-[family-name:var(--font-headline)]">
                    {item.title}
                  </h3>
                  <p className="text-sm text-fg-muted leading-relaxed font-[family-name:var(--font-body)]">
                    {item.text}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* What Makes VoiceLink Different */}
      <section className="bg-surface-low">
        <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-10 py-20 sm:py-24">
          <div className="max-w-3xl">
            <h2 className="text-2xl sm:text-3xl font-bold text-primary mb-6 font-[family-name:var(--font-headline)]">
              What makes VoiceLink different
            </h2>
            <div className="space-y-5 text-fg-muted leading-relaxed font-[family-name:var(--font-body)]">
              <p>
                VoiceLink is not a research project or a one-off data collection effort. It is
                public-interest infrastructure -- a repeatable, scalable pipeline designed to be
                deployed across radio stations and languages.
              </p>
              <p>
                The entire codebase is open-source under the Mozilla Public License 2.0. The
                architecture is SIP/WebRTC compatible with no vendor lock-in, ensuring any
                organisation can deploy, audit, and extend the system independently.
              </p>
              <p>
                Community ownership is central to the model. Language Advisory Councils comprising
                native speakers, cultural leaders, and linguistics experts guide quality assurance
                and validation for each language. This community-led approach ensures data
                integrity and cultural appropriateness.
              </p>
              <p>
                The pipeline is fully automated from archive ingestion through clip generation,
                with human review at the quality gate. Every stage is tracked through a live
                operations dashboard, providing full transparency into data provenance and
                processing status. VoiceLink includes a replication framework designed for
                deployment across Sub-Saharan Africa, with training programmes for local developers.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Neuravox */}
      <section className="bg-bg">
        <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-10 py-20 sm:py-24">
          <div className="max-w-3xl">
            <h2 className="text-2xl sm:text-3xl font-bold text-primary mb-6 font-[family-name:var(--font-headline)]">
              Built by Neuravox
            </h2>
            <div className="space-y-5 text-fg-muted leading-relaxed font-[family-name:var(--font-body)]">
              <p>
                VoiceLink is built and operated by{" "}
                <a
                  href="https://neuravox.org"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-secondary hover:underline"
                >
                  Neuravox
                </a>
                , a Community Interest Company based in Kampala, Uganda, focused on ethical AI
                governance, public interest technology, and community-led innovation across Africa.
                The project is led by Gideon Abako.
              </p>
              <p>
                VoiceLink is supported by the Mozilla Common Voice Public API Developer Fund
                to demonstrate that radio infrastructure can serve as a scalable, community-owned
                channel for multilingual speech data collection.
              </p>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
