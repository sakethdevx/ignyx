import Link from "next/link";
import { ArrowUpRight, FileText, TerminalSquare } from "lucide-react";
import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/glass-card";
import { externalDocsUrl } from "@/lib/site";

const docsPages = [
  { slug: [], title: "Documentation", description: "Browse the full Ignyx documentation." },
  {
    slug: ["quickstart"],
    title: "Quickstart",
    description: "Install Ignyx, define your first route, and run your first app.",
  },
  {
    slug: ["routing"],
    title: "Routing",
    description: "Learn how Ignyx structures endpoints, params, and modular routers.",
  },
  {
    slug: ["request"],
    title: "Request Handling",
    description: "Inspect request bodies, headers, params, and helper utilities.",
  },
  {
    slug: ["middleware"],
    title: "Middleware",
    description: "Understand the middleware model for logging, CORS, errors, and more.",
  },
  {
    slug: ["validation"],
    title: "Validation",
    description: "Use typed request validation and Pydantic-backed schemas effectively.",
  },
  {
    slug: ["security"],
    title: "Security",
    description: "Explore sessions, auth utilities, and production-minded guard rails.",
  },
  {
    slug: ["deployment"],
    title: "Deployment",
    description: "See how to deploy Ignyx-powered services cleanly in production.",
  },
];

type DocsPageParams = {
  slug?: string[];
};

export function generateStaticParams() {
  return docsPages.map((page) => ({ slug: page.slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<DocsPageParams>;
}): Promise<Metadata> {
  const resolved = await params;
  const slug = resolved.slug ?? [];
  const page = docsPages.find(
    (entry) => entry.slug.join("/") === slug.join("/"),
  );

  if (!page) {
    return {
      title: "Docs | Ignyx",
    };
  }

  return {
    title: `${page.title} | Ignyx Docs`,
    description: page.description,
  };
}

export default async function DocsBridgePage({
  params,
}: {
  params: Promise<DocsPageParams>;
}) {
  const resolved = await params;
  const slug = resolved.slug ?? [];
  const page = docsPages.find(
    (entry) => entry.slug.join("/") === slug.join("/"),
  );

  if (!page) {
    notFound();
  }

  const path = slug.length === 0 ? "/" : `/${slug.join("/")}/`;
  const docsUrl = externalDocsUrl(path);

  return (
    <main className="container flex min-h-[70vh] items-center py-24">
      <GlassCard className="mx-auto max-w-3xl rounded-[32px] p-8 sm:p-10">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-electric-400/12 text-electric-400">
          <FileText className="h-7 w-7" />
        </div>

        <h1 className="mt-6 text-4xl font-semibold text-white">{page.title}</h1>
        <p className="mt-4 text-base leading-8 text-muted">{page.description}</p>
        <p className="mt-4 text-sm leading-7 text-muted">
          In local Next.js development, the marketing site runs on port 3000 while the full MkDocs
          documentation is published separately. This bridge keeps `/docs/` links from breaking.
        </p>

        <div className="mt-8 flex flex-col gap-4 sm:flex-row">
          <Button asChild>
            <Link href={docsUrl}>
              Open documentation
              <ArrowUpRight className="h-4 w-4" />
            </Link>
          </Button>
          <Button asChild variant="secondary">
            <Link href="/">Back to homepage</Link>
          </Button>
        </div>

        <div className="mt-10 rounded-[24px] border border-white/10 bg-[#07111d] p-5">
          <div className="flex items-center gap-2 text-xs uppercase tracking-[0.26em] text-muted">
            <TerminalSquare className="h-4 w-4" />
            Local docs option
          </div>
          <pre className="mt-4 overflow-x-auto font-mono text-sm leading-7 text-slate-200">
{`pip install mkdocs-material
mkdocs serve`}
          </pre>
          <p className="mt-4 text-sm leading-7 text-muted">
            If you want the docs running locally too, start MkDocs and open the served docs site in a
            second tab.
          </p>
        </div>
      </GlassCard>
    </main>
  );
}
