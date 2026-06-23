import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { AuthGuard } from "@/components/AuthGuard";
import { Header } from "@/components/Header";
import { Toaster } from "@/components/ui/sonner";
import { Providers } from "./providers";

const inter = Inter({
  variable: "--font-sans",
  subsets: ["latin"],
});

const mono = JetBrains_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Azure RAG Assistant",
  description: "Wgrywaj PDF-y i zadawaj pytania oparte na treści dokumentów.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="pl"
      className={`${inter.variable} ${mono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-background text-foreground">
        <Providers>
          <AuthGuard>
            <Header />
            <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-8">{children}</main>
          </AuthGuard>
        </Providers>
        <Toaster richColors position="top-center" />
      </body>
    </html>
  );
}
