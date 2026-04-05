import Link from "next/link";
import { Github, Mail, MessageSquareMore, ScrollText } from "lucide-react";
import { docsPath, siteConfig } from "@/lib/site";

const footerLinks = [
  { label: "Docs", href: docsPath(), icon: ScrollText },
  { label: "GitHub", href: siteConfig.githubUrl, icon: Github },
  { label: "Community", href: `${siteConfig.githubUrl}/discussions`, icon: MessageSquareMore },
  { label: "Contact", href: "mailto:hello@ignyx.dev", icon: Mail },
];

export function SiteFooter() {
  return (
    <footer className="border-t border-white/6 py-10">
      <div className="container flex flex-col gap-8 md:flex-row md:items-center md:justify-between">
        <div>
          <div className="font-display text-xl font-semibold text-white">Ignyx</div>
          <p className="mt-2 max-w-lg text-sm text-muted">
            A premium foundation for Python applications that need speed, structure, and a production story teams can trust.
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          {footerLinks.map((link) => (
            <Link
              key={link.label}
              href={link.href}
              className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-4 py-2 text-sm text-muted transition-colors hover:text-white"
            >
              <link.icon className="h-4 w-4" />
              {link.label}
            </Link>
          ))}
        </div>
      </div>
    </footer>
  );
}
