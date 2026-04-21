import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Contact - VoiceLink",
  description:
    "Get in touch about radio station partnerships, research collaboration, or funding VoiceLink's speech data infrastructure.",
};

const channels = [
  {
    title: "Radio station partnerships",
    description:
      "If you operate a radio station broadcasting in an African language and are interested in contributing your archives to open speech datasets, we would like to hear from you.",
    contact: "partnerships@neuravox.org",
  },
  {
    title: "Research collaboration",
    description:
      "VoiceLink welcomes collaboration with researchers working on speech technology, natural language processing, and language documentation for African languages.",
    contact: "research@neuravox.org",
  },
  {
    title: "Funding & support",
    description:
      "VoiceLink is public-interest infrastructure. We work with funders, foundations, and institutions that share our commitment to linguistic inclusion in technology.",
    contact: "contact@neuravox.org",
  },
];

export default function ContactPage() {
  return (
    <>
      {/* Header */}
      <section className="bg-surface-low">
        <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-10 py-20 sm:py-28">
          <p className="text-sm font-semibold tracking-widest uppercase text-secondary mb-6 font-[family-name:var(--font-label)]">
            Get in Touch
          </p>
          <h1 className="text-4xl sm:text-5xl font-bold tracking-tight text-primary leading-[1.1] max-w-3xl font-[family-name:var(--font-headline)]">
            Work with us
          </h1>
          <p className="mt-8 text-lg text-fg-muted max-w-2xl leading-relaxed font-[family-name:var(--font-body)]">
            VoiceLink is built through partnerships. Whether you represent a radio station,
            research institution, or funding body, there are meaningful ways to contribute to
            speech data infrastructure for African languages.
          </p>
        </div>
      </section>

      {/* Contact channels */}
      <section className="bg-bg">
        <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-10 py-20 sm:py-24">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {channels.map((channel) => (
              <div
                key={channel.title}
                className="bg-surface-low rounded-2xl p-8 sm:p-10 flex flex-col"
              >
                <h2 className="text-lg font-semibold text-fg mb-4 font-[family-name:var(--font-headline)]">
                  {channel.title}
                </h2>
                <p className="text-sm text-fg-muted leading-relaxed mb-8 flex-1 font-[family-name:var(--font-body)]">
                  {channel.description}
                </p>
                <a
                  href={`mailto:${channel.contact}`}
                  className="text-sm font-semibold text-secondary hover:underline font-[family-name:var(--font-label)]"
                >
                  {channel.contact}
                </a>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Neuravox */}
      <section className="bg-surface-low">
        <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-10 py-20 sm:py-24">
          <div className="max-w-3xl">
            <h2 className="text-2xl sm:text-3xl font-bold text-primary mb-6 font-[family-name:var(--font-headline)]">
              About the team
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
                , a Community Interest Company focused on ethical AI governance, public interest
                technology, and community-led innovation across Africa.
              </p>
              <p>
                For general enquiries about Neuravox and its broader work, visit{" "}
                <a
                  href="https://neuravox.org"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-secondary hover:underline"
                >
                  neuravox.org
                </a>
                .
              </p>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
