import Link from "next/link";

import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/glass-card";
import { siteConfig } from "@/lib/site";

export function CtaSection() {
  return (
    <section className="container py-24 sm:py-28">
      <GlassCard className="panel-line relative overflow-hidden rounded-[36px] px-8 py-12 sm:px-12">
        <div className="absolute inset-0 bg-gradient-to-r from-electric-500/12 via-transparent to-violet-500/12" />
        <div className="relative flex flex-col gap-8 lg:flex-row lg:items-center lg:justify-between">
          <div className="max-w-2xl">
            <p className="text-sm uppercase tracking-[0.28em] text-electric-400">Launch with confidence</p>
            <h2 className="mt-4 text-4xl font-semibold tracking-tight text-white sm:text-5xl">
              Start building with Ignyx today
            </h2>
            <p className="mt-4 text-base leading-8 text-muted">
              Move faster on product work and keep a stronger technical story for performance, docs, and production behavior from the start.
            </p>
          </div>
          <div className="flex flex-col gap-4 sm:flex-row">
            <Button asChild size="lg">
              <Link href="#getting-started">Get Started</Link>
            </Button>
            <Button asChild size="lg" variant="secondary">
              <Link href={siteConfig.githubUrl}>View GitHub</Link>
            </Button>
          </div>
        </div>
      </GlassCard>
    </section>
  );
}
