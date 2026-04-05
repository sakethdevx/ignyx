import Link from "next/link";

import { Button } from "@/components/ui/button";
import { docsPath, siteConfig } from "@/lib/site";

const navItems = [
  { label: "Features", href: "#features" },
  { label: "Why Ignyx", href: "#why-ignyx" },
  { label: "Docs Preview", href: "#docs-preview" },
  { label: "GitHub", href: siteConfig.githubUrl },
];

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-40 border-b border-white/6 bg-[#090d16]/70 backdrop-blur-2xl">
      <div className="container flex h-20 items-center justify-between">
        <Link href="/" className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-electric-400 to-violet-500 text-lg font-semibold text-white shadow-glow">
            I
          </div>
          <div>
            <div className="font-display text-lg font-semibold tracking-tight text-white">Ignyx</div>
            <div className="text-xs uppercase tracking-[0.28em] text-muted">Python + Rust</div>
          </div>
        </Link>

        <nav className="hidden items-center gap-8 text-sm text-muted md:flex">
          {navItems.map((item) => (
            <Link
              key={item.label}
              href={item.href}
              className="transition-colors duration-300 hover:text-white"
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="flex items-center gap-3">
          <Button asChild variant="ghost" className="hidden sm:inline-flex">
            <Link href={docsPath()}>View Docs</Link>
          </Button>
          <Button asChild>
            <Link href="#getting-started">Get Started</Link>
          </Button>
        </div>
      </div>
    </header>
  );
}
