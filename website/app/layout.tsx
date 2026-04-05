import type { Metadata } from "next";
import type { ReactNode } from "react";

import { withBasePath } from "@/lib/site";

import "./globals.css";

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "https://sakethdevx.github.io";
const socialImagePath = withBasePath("/ignyx-logo.svg");
const faviconPath = withBasePath("/favicon.svg");

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: "Ignyx | The Next-Gen Python Framework",
  description:
    "Ignyx is a high-performance Python framework powered by a Rust core for scalable APIs, services, and developer platforms.",
  openGraph: {
    title: "Ignyx | The Next-Gen Python Framework",
    description:
      "Ignyx is a high-performance Python framework powered by a Rust core for scalable APIs, services, and developer platforms.",
    images: [
      {
        url: socialImagePath,
        width: 820,
        height: 220,
        alt: "Ignyx logo",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Ignyx | The Next-Gen Python Framework",
    description:
      "Ignyx is a high-performance Python framework powered by a Rust core for scalable APIs, services, and developer platforms.",
    images: [socialImagePath],
  },
  icons: {
    icon: faviconPath,
    shortcut: faviconPath,
    apple: faviconPath,
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="bg-background text-foreground">
        {children}
      </body>
    </html>
  );
}
