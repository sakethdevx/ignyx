import Image from "next/image";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { marketingDocsHref, siteConfig, withBasePath } from "@/lib/site";

const navItems = [
  { label: "Features", href: "#features" },
  { label: "Why Ignyx", href: "#why-ignyx" },
  { label: "Docs Preview", href: "#docs-preview" },
  { label: "GitHub", href: siteConfig.githubUrl },
];

const logoPath = withBasePath("/ignyx-logo.svg");

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-40 border-b border-white/6 bg-[#090d16]/70 backdrop-blur-2xl">
      <div className="container flex h-20 items-center justify-between">
        <Link href="/" className="flex items-center">
          <div className="flex h-12 w-[146px] items-center overflow-hidden rounded-2xl border border-white/10 bg-[rgba(248,251,255,0.94)] px-2 py-1.5 shadow-[0_18px_40px_rgba(0,0,0,0.24)] backdrop-blur-sm sm:w-[158px]">
            <div className="relative -ml-0.5 h-full w-[150px] sm:w-[162px]">
              <Image
                src={logoPath}
                alt="Ignyx logo"
                fill
                sizes="(min-width: 640px) 162px, 150px"
                className="object-contain object-left"
              />
            </div>
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
            <a href={marketingDocsHref()}>View Docs</a>
          </Button>
          <Button asChild>
            <Link href="#getting-started">Get Started</Link>
          </Button>
        </div>
      </div>
    </header>
  );
}
