import type { Metadata } from "next";
import Image from "next/image";

export const metadata: Metadata = {
  title: "Partners — VoiceLink",
  description:
    "VoiceLink partners with CBS Radio 88.8 FM and Voice of Teso 88.4 FM to build open speech datasets for Luganda and Ateso.",
};

export default function PartnersPage() {
  return (
    <>
      {/* Header */}
      <section className="bg-surface-low">
        <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-10 py-20 sm:py-28">
          <p className="text-sm font-semibold tracking-widest uppercase text-secondary mb-6 font-[family-name:var(--font-label)]">
            Radio Station Partners
          </p>
          <h1 className="text-4xl sm:text-5xl font-bold tracking-tight text-primary leading-[1.1] max-w-3xl font-[family-name:var(--font-headline)]">
            Working with the institutions that serve language communities
          </h1>
          <p className="mt-8 text-lg text-fg-muted max-w-2xl leading-relaxed font-[family-name:var(--font-body)]">
            VoiceLink partners with established radio stations whose archives represent decades
            of natural speech in African languages. Each partnership is built on formal licensing
            agreements and informed consent.
          </p>
        </div>
      </section>

      {/* CBS Radio */}
      <section className="bg-bg">
        <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-10 py-20 sm:py-24">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-16 items-start">
            <div className="lg:col-span-4">
              <div className="bg-surface-low rounded-2xl p-10 flex items-center justify-center">
                <Image
                  src="/cbs-logo.png"
                  alt="CBS Radio 88.8 FM logo"
                  width={240}
                  height={100}
                  className="object-contain"
                />
              </div>
            </div>
            <div className="lg:col-span-8">
              <h2 className="text-2xl sm:text-3xl font-bold text-primary mb-2 font-[family-name:var(--font-headline)]">
                CBS Radio 88.8 FM
              </h2>
              <p className="text-sm font-medium text-secondary mb-6 font-[family-name:var(--font-label)]">
                Kampala, Uganda &middot; Luganda
              </p>
              <div className="space-y-5 text-fg-muted leading-relaxed font-[family-name:var(--font-body)]">
                <p>
                  CBS Radio 88.8 FM is Uganda&apos;s biggest cultural institution, broadcasting
                  primarily in Luganda since 1953. The station serves the Buganda Kingdom&apos;s
                  cultural community and reaches millions of listeners across central Uganda.
                  Luganda is the most widely spoken indigenous language in Uganda at 22.2% of
                  the population.
                </p>
                <p>
                  The CBS archive represents one of the largest collections of recorded Luganda
                  speech in existence -- rich with spontaneous conversation, code-switching, and
                  cultural context from decades of call-in programmes and live broadcasts.
                  VoiceLink has processed over 512 hours from these archives, generating more
                  than 128,000 individual speech clips for contribution to Mozilla Common Voice
                  and other open repositories.
                </p>
              </div>
              <div className="mt-8 grid grid-cols-2 gap-6">
                <div>
                  <p className="text-3xl font-bold text-secondary font-[family-name:var(--font-label)]">
                    512+
                  </p>
                  <p className="mt-1 text-sm text-fg-muted font-[family-name:var(--font-body)]">
                    Hours processed
                  </p>
                </div>
                <div>
                  <p className="text-3xl font-bold text-secondary font-[family-name:var(--font-label)]">
                    128k+
                  </p>
                  <p className="mt-1 text-sm text-fg-muted font-[family-name:var(--font-body)]">
                    Clips generated
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Voice of Teso */}
      <section className="bg-surface-low">
        <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-10 py-20 sm:py-24">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-16 items-start">
            <div className="lg:col-span-4">
              <div className="bg-surface-container rounded-2xl p-10 flex items-center justify-center">
                <Image
                  src="/vot-logo.webp"
                  alt="Voice of Teso 88.4 FM logo"
                  width={240}
                  height={100}
                  className="object-contain"
                />
              </div>
            </div>
            <div className="lg:col-span-8">
              <h2 className="text-2xl sm:text-3xl font-bold text-primary mb-2 font-[family-name:var(--font-headline)]">
                Voice of Teso 88.4 FM
              </h2>
              <p className="text-sm font-medium text-secondary mb-6 font-[family-name:var(--font-label)]">
                Soroti, Uganda &middot; Ateso
              </p>
              <div className="space-y-5 text-fg-muted leading-relaxed font-[family-name:var(--font-body)]">
                <p>
                  Voice of Teso is a community radio station based in Soroti, eastern Uganda,
                  broadcasting in Ateso -- the language of the Iteso people. The station serves
                  as a vital cultural and information hub for the Teso sub-region.
                </p>
                <p>
                  Ateso accounts for 12.1% of Uganda&apos;s linguistic landscape and is spoken
                  by approximately 3.2 million people, yet it remains significantly
                  underrepresented in speech technology. The Voice of Teso partnership brings
                  a second language into the VoiceLink pipeline, demonstrating the model&apos;s
                  scalability across stations and languages.
                </p>
              </div>
              <div className="mt-8">
                <p className="text-sm font-medium text-secondary font-[family-name:var(--font-label)]">
                  Pipeline integration in progress
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Partnership model */}
      <section className="bg-bg">
        <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-10 py-20 sm:py-24">
          <div className="max-w-3xl">
            <h2 className="text-2xl sm:text-3xl font-bold text-primary mb-6 font-[family-name:var(--font-headline)]">
              Partnership model
            </h2>
            <div className="space-y-5 text-fg-muted leading-relaxed font-[family-name:var(--font-body)]">
              <p>
                VoiceLink operates on a value exchange model. Every partnership is governed by
                a formal agreement that defines data usage rights, attribution, and the terms
                under which processed speech data may be contributed to open datasets.
              </p>
              <p>
                In return for access to broadcast audio, partner stations receive operational
                tools and insights that help them better understand and serve their audiences.
                Partner stations retain ownership of their original recordings.
              </p>
              <p>
                VoiceLink provides the technical infrastructure for processing and contributes
                the resulting speech data to open repositories under licenses that ensure broad
                access while respecting the source communities.
              </p>
              <p>
                We are actively seeking additional radio station partners across Africa,
                particularly those broadcasting in languages with limited existing speech
                data resources.
              </p>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
