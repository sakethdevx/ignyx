import Image from "next/image";

import { Github, Mail, MessageSquareMore, ScrollText } from "lucide-react";
import { marketingDocsHref, siteConfig, withBasePath } from "@/lib/site";

const footerLinks = [
  { label: "Docs", href: marketingDocsHref(), icon: ScrollText },
  { label: "GitHub", href: siteConfig.githubUrl, icon: Github },
  { label: "Community", href: `${siteConfig.githubUrl}/discussions`, icon: MessageSquareMore },
  { label: "Contact", href: "mailto:hello@ignyx.dev", icon: Mail },
];

const logoPath = withBasePath("/ignyx-logo.svg");

export function SiteFooter() {
  return (
    <footer className="border-t border-white/6 py-10">
      <div className="container flex flex-col gap-8 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-5">
          <div className="flex h-[72px] w-[178px] items-center overflow-hidden rounded-[24px] border border-white/10 bg-[rgba(248,251,255,0.94)] px-3 py-2.5 shadow-[0_18px_40px_rgba(0,0,0,0.24)] backdrop-blur-sm sm:w-[190px]">
            <div className="relative -ml-0.5 h-full w-[182px] sm:w-[194px]">
              <Image
                src={logoPath}
                alt="Ignyx logo"
                fill
                sizes="(min-width: 640px) 194px, 182px"
                className="object-contain object-left"
              />
            </div>
          </div>
          <div>
            <p className="mt-2 max-w-lg text-sm text-muted">
              A premium foundation for Python applications that need speed, structure, and a production story teams can trust.
            </p>
          </div>
        </div>
        <div className="flex flex-wrap gap-3">
          {footerLinks.map((link) => (
            <a
              key={link.label}
              href={link.href}
              className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-4 py-2 text-sm text-muted transition-colors hover:text-white"
            >
              <link.icon className="h-4 w-4" />
              {link.label}
            </a>
          ))}
        </div>
      </div>
    </footer>
  );
}
