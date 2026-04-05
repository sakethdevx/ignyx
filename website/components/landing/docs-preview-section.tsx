"use client";

import Link from "next/link";
import { Search, TerminalSquare } from "lucide-react";

import { Reveal } from "@/components/landing/reveal";
import { SectionHeading } from "@/components/landing/section-heading";
import { GlassCard } from "@/components/ui/glass-card";
import { Button } from "@/components/ui/button";
import { docsPath } from "@/lib/site";

const docNav = [
  "Quickstart",
  "Routing",
  "Requests",
  "Middleware",
  "Validation",
  "Security",
  "Deployment",
];

export function DocsPreviewSection() {
  return (
    <section id="docs-preview" className="container py-24 sm:py-28">
      <Reveal>
        <SectionHeading
          eyebrow="Documentation"
          title="A docs experience that feels productized, not dumped from a generator"
          description="The new website is set up to evolve into a richer doc surface with search, structured navigation, and visual examples that match the product quality bar."
          align="center"
        />
      </Reveal>

      <Reveal delay={0.1}>
        <GlassCard className="mt-14 overflow-hidden rounded-[34px] p-0">
          <div className="grid lg:grid-cols-[260px_1fr]">
            <aside className="border-b border-white/10 bg-white/[0.03] p-6 lg:border-b-0 lg:border-r">
              <div className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-muted">
                <Search className="h-4 w-4" />
                Search docs
              </div>
              <div className="mt-6 space-y-2">
                {docNav.map((item, index) => (
                  <div
                    key={item}
                    className={`rounded-2xl px-4 py-3 text-sm ${
                      index === 0
                        ? "bg-electric-400/12 text-white"
                        : "text-muted transition-colors hover:bg-white/[0.05] hover:text-white"
                    }`}
                  >
                    {item}
                  </div>
                ))}
              </div>
            </aside>

            <div className="p-6 sm:p-8">
              <div className="flex items-center gap-3 text-sm text-electric-400">
                <TerminalSquare className="h-4 w-4" />
                Documentation preview
              </div>
              <h3 className="mt-4 text-3xl font-semibold text-white">Quickstart in under five minutes</h3>
              <p className="mt-4 max-w-2xl text-sm leading-7 text-muted">
                Install Ignyx, define your first route, and ship a framework that already thinks about validation, docs, performance, and deployment as part of the same story.
              </p>
              <div className="mt-6">
                <Button asChild variant="secondary">
                  <Link href={docsPath()}>Open full documentation</Link>
                </Button>
              </div>

              <div className="mt-8 rounded-[28px] border border-white/10 bg-[#07111d] p-5">
                <div className="flex items-center gap-2 text-xs uppercase tracking-[0.26em] text-muted">
                  Quickstart snippet
                </div>
                <pre className="mt-4 overflow-x-auto font-mono text-sm leading-7 text-slate-200">
{`from ignyx import Ignyx

app = Ignyx()

@app.get("/")
async def root():
    return {"message": "Hello from Ignyx"}

app.run(host="0.0.0.0", port=8000)`}
                </pre>
              </div>
            </div>
          </div>
        </GlassCard>
      </Reveal>
    </section>
  );
}
