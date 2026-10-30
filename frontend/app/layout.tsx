import type { Metadata, Viewport } from "next";
import "./globals.css";

export const viewport: Viewport = {
  themeColor: "#FAF9F6",
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
};

export const metadata: Metadata = {
  title: "Common Ground — Everyone's taste. One trip.",
  description:
    "Taste-fair group trip planning engine powered by Qloo's Cultural Intelligence. Finding shared affinities and mathematically balanced compromises across music, food, and culture.",
  metadataBase: new URL(
    process.env.NEXT_PUBLIC_APP_URL || "https://commonground.app"
  ),
  keywords: [
    "Qloo",
    "Cultural Intelligence",
    "Group Travel",
    "Taste Graph",
    "Fairness Scoring",
    "Trip Planner",
    "Lisbon",
    "Tokyo",
  ],
  authors: [{ name: "Common Ground Team" }],
  openGraph: {
    title: "Common Ground — Everyone's taste. One trip.",
    description:
      "Taste-fair group travel powered by Qloo's Cultural AI. Balances everyone's taste with mathematical fairness guarantees.",
    url: "https://commonground.app",
    siteName: "Common Ground",
    images: [
      {
        url: "/og-image.png",
        width: 1200,
        height: 630,
        alt: "Common Ground — Taste-Fair Group Trip Planner",
      },
    ],
    locale: "en_US",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Common Ground — Everyone's taste. One trip.",
    description:
      "Taste-fair group travel powered by Qloo's Cultural AI. Mathematical fairness across music, dining, and art.",
    images: ["/og-image.png"],
  },
  icons: {
    icon: "/icon.svg",
    apple: "/apple-icon.svg",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="scroll-smooth">
      <body className="min-h-screen bg-offwhite text-nearblack selection:bg-brand-violet/15 selection:text-nearblack font-sans antialiased">
        {/* Skip to main content for screen readers / keyboard navigation */}
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2 focus:bg-nearblack focus:text-white focus:rounded-pill focus:font-mono focus:text-xs"
        >
          Skip to main content
        </a>
        {/* Delicate Auralis-style thin blue/violet viewport border */}
        <div className="viewport-frame" aria-hidden="true" />
        <div id="main-content">{children}</div>
      </body>
    </html>
  );
}
