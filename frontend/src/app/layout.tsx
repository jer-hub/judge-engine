import type { Metadata } from "next";
import { IBM_Plex_Sans, IBM_Plex_Mono } from "next/font/google";

import { NavBar } from "@/components/NavBar";
import { Providers } from "@/components/Providers";

import "./globals.css";

const sans = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-sans",
});

const mono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
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
