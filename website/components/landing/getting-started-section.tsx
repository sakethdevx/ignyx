"use client";

import { motion } from "framer-motion";

import { Reveal } from "@/components/landing/reveal";
import { SectionHeading } from "@/components/landing/section-heading";
import { GlassCard } from "@/components/ui/glass-card";

const steps = [
  {
    step: "01",
    title: "Install",
    snippet: "pip install ignyx",
  },
  {
    step: "02",
    title: "Configure",
    snippet: "app = Ignyx(title='Launch API')",
  },
  {
    step: "03",
    title: "Run",
    snippet: "python app.py",
  },
];

export function GettingStartedSection() {
  return (
    <section id="getting-started" className="container py-24 sm:py-28">
      <div className="grid gap-10 lg:grid-cols-[0.45fr_0.55fr] lg:items-center">
        <Reveal>
          <SectionHeading
            eyebrow="Getting Started"
            title="From blank repo to running API in three clear steps"
            description="The first impression matters. Ignyx keeps setup compact so your team gets to business logic quickly without sacrificing a serious runtime foundation."
          />
        </Reveal>

        <Reveal delay={0.1}>
          <GlassCard className="overflow-hidden rounded-[32px] p-0">
            <div className="border-b border-white/10 bg-white/[0.04] px-5 py-4 text-sm text-muted">
              terminal
            </div>
            <div className="space-y-4 bg-[#07111d] p-6">
              {steps.map((item, index) => (
                <motion.div
                  key={item.step}
                  initial={{ opacity: 0, x: 18 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.45, delay: index * 0.08 }}
                  className="rounded-[24px] border border-white/8 bg-white/[0.04] p-4"
                >
                  <div className="flex items-center gap-3">
                    <span className="rounded-full bg-electric-400/15 px-3 py-1 text-xs font-semibold tracking-[0.24em] text-electric-400">
                      {item.step}
                    </span>
                    <span className="text-sm font-medium text-white">{item.title}</span>
                  </div>
                  <pre className="mt-3 overflow-x-auto font-mono text-sm text-slate-200">
                    <span className="text-electric-400">$</span> {item.snippet}
                  </pre>
                </motion.div>
              ))}
            </div>
          </GlassCard>
        </Reveal>
      </div>
    </section>
  );
}
