import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Nav from "./components/Nav";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "VoiceLink — Ingestion Pipeline",
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
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-bg text-fg">
        <Nav />
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {children}
        </main>
        <footer className="border-t border-border">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-5 flex flex-col sm:flex-row gap-2 sm:gap-4 items-start sm:items-center justify-between">
            <p className="text-xs text-fg-subtle">
              VoiceLink Uganda · Read-only ingestion view
            </p>
            <p className="text-[11px] text-fg-subtle tracking-wide">
              Data served by Supabase · Theme follows your system preference
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
