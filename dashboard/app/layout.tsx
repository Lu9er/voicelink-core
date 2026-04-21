import type { Metadata } from "next";
import { Manrope, Inter, Space_Grotesk } from "next/font/google";
import Nav from "./components/Nav";
import "./globals.css";

const manrope = Manrope({
  variable: "--font-manrope",
  subsets: ["latin"],
});

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const spaceGrotesk = Space_Grotesk({
  variable: "--font-space-grotesk",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "VoiceLink - Ingestion Pipeline",
  description:
    "Read-only dashboard for the VoiceLink speech data ingestion pipeline.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${manrope.variable} ${inter.variable} ${spaceGrotesk.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-bg text-fg">
        <Nav />
        <main className="flex-1 max-w-7xl w-full mx-auto px-6 sm:px-8 lg:px-10 py-10">
          {children}
        </main>
        <footer className="bg-surface-low">
          <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-10 py-6 flex flex-col sm:flex-row gap-2 sm:gap-4 items-start sm:items-center justify-between">
            <p className="text-xs text-fg-subtle font-[family-name:var(--font-body)]">
              VoiceLink Uganda · Read-only ingestion view
            </p>
            <p className="text-[11px] text-fg-subtle tracking-wide font-[family-name:var(--font-body)]">
              Data served by Supabase · Theme follows your system preference
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
