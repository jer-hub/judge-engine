import type { Metadata } from "next";
import localFont from "next/font/local";

import { NavBar } from "@/components/NavBar";
import { Providers } from "@/components/Providers";

import "./globals.css";

// IBM Plex (SIL OFL, see fonts/*-OFL.txt), bundled in the repo: next/font/google
// fetched them from Google at build time, which made builds flaky and needed
// internet access.
const sans = localFont({
  src: [
    { path: "./fonts/ibm-plex-sans-latin-400-normal.woff2", weight: "400" },
    { path: "./fonts/ibm-plex-sans-latin-500-normal.woff2", weight: "500" },
    { path: "./fonts/ibm-plex-sans-latin-600-normal.woff2", weight: "600" },
    { path: "./fonts/ibm-plex-sans-latin-700-normal.woff2", weight: "700" },
  ],
  variable: "--font-sans",
});

const mono = localFont({
  src: [
    { path: "./fonts/ibm-plex-mono-latin-400-normal.woff2", weight: "400" },
    { path: "./fonts/ibm-plex-mono-latin-500-normal.woff2", weight: "500" },
  ],
  variable: "--font-mono",
});

export const metadata: Metadata = {
  title: "Judge Engine",
  description: "School competitive programming platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${sans.variable} ${mono.variable} min-h-screen bg-slate-950 font-sans text-slate-100 antialiased`}
      >
        <Providers>
          <NavBar />
          <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>
        </Providers>
      </body>
    </html>
  );
}
