import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Nav } from "@/components/Nav";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Job Market Intelligence",
  description:
    "Market intelligence platform: an ETL pipeline that keeps tabs on Google Careers postings, with analytics on skills, seniority, locations and compensation.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="min-h-screen bg-ink-950">
        <Nav />
        <main className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          {children}
        </main>
        <footer className="mx-auto w-full max-w-7xl px-4 pb-10 text-xs text-slate-600 sm:px-6 lg:px-8">
          Job Market Intelligence · ETL snapshot of Google Careers postings · Not affiliated with Google
        </footer>
      </body>
    </html>
  );
}