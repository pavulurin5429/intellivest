import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "IntelliVest — Multi-Agent Investment Intelligence",
  description: "5-Agent LLM Investment Intelligence & Credit Risk Platform",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body className="min-h-screen">{children}</body>
    </html>
  );
}
