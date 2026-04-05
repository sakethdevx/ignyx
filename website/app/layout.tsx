import type { Metadata } from "next";
import type { ReactNode } from "react";

import "./globals.css";

export const metadata: Metadata = {
  title: "Ignyx | The Next-Gen Python Framework",
  description:
    "Ignyx is a high-performance Python framework powered by a Rust core for scalable APIs, services, and developer platforms.",
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
