import type { Metadata } from "next";
import "./globals.css";
import Link from "next/link";

export const metadata: Metadata = {
  title: "BugForge — AI Chaos Engineering",
  description: "Generate and execute multi-layered chaos scenarios with AI",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50">
        <nav className="bg-white border-b border-gray-200 px-6 py-3 flex items-center gap-6">
          <Link href="/" className="font-bold text-lg text-gray-900 tracking-tight">
            🔥 BugForge
          </Link>
          <Link href="/architectures/new" className="text-sm text-gray-600 hover:text-blue-600">
            New Architecture
          </Link>
          <Link href="/architectures" className="text-sm text-gray-600 hover:text-blue-600">
            Architectures
          </Link>
        </nav>
        <main className="max-w-5xl mx-auto px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
