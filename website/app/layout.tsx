import type { Metadata } from "next";
import { Manrope, Inter, Space_Grotesk } from "next/font/google";
import Nav from "./components/Nav";
import Footer from "./components/Footer";
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
  title: "VoiceLink Uganda - Radio Call Integration for Multilingual Speech Data Collection",
  description:
    "VoiceLink integrates with radio stations to capture natural speech for Mozilla Common Voice while providing stations with call analytics. Open-source, community-owned. A Neuravox project.",
  openGraph: {
    title: "VoiceLink Uganda - Multilingual Speech Data Collection",
    description:
      "Radio call integration for multilingual speech data collection across Uganda. Open-source infrastructure by Neuravox, supported by Mozilla.",
    url: "https://voicelink.cloud",
    siteName: "VoiceLink",
    type: "website",
  },
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
        <main className="flex-1">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
