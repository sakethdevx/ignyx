"use client";

import { motion } from "framer-motion";
import { Check, Minus } from "lucide-react";

import { Reveal } from "@/components/landing/reveal";
import { SectionHeading } from "@/components/landing/section-heading";
import { GlassCard } from "@/components/ui/glass-card";

type ComparisonRow = {
  capability: string;
  values: [boolean, boolean, boolean];
};

const comparison: ComparisonRow[] = [
  { capability: "Rust-backed request core", values: [true, false, false] },
  { capability: "FastAPI-style developer ergonomics", values: [true, true, false] },
  { capability: "Built-in docs and schema flow", values: [true, true, false] },
  { capability: "Native zero-copy upload path", values: [true, false, false] },
  { capability: "Observability-focused request spans", values: [true, false, false] },
  { capability: "Enterprise-ready middleware surface", values: [true, true, true] },
];

export function WhyIgnyxSection() {
  return (
    <section id="why-ignyx" className="container py-24 sm:py-28">
      <Reveal>
        <SectionHeading
          eyebrow="Why Ignyx"
          title="A framework that respects Python, but refuses to settle for Python-only ceilings"
          description="Ignyx is for teams that want FastAPI-level approachability with a runtime and architecture story that grows into more demanding environments."
          align="center"
        />
      </Reveal>

      <Reveal delay={0.1}>
        <GlassCard className="mt-14 overflow-hidden rounded-[32px] p-0">
          <div className="grid grid-cols-[1.4fr_repeat(3,minmax(0,1fr))] border-b border-white/10 bg-white/[0.04] px-6 py-5 text-sm font-medium text-white">
            <div>Capability</div>
            <div className="text-center">Ignyx</div>
            <div className="text-center">FastAPI</div>
            <div className="text-center">Flask</div>
          </div>
          <div>
            {comparison.map((row, index) => (
              <motion.div
                key={row.capability}
                initial={{ opacity: 0, y: 18 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: index * 0.05 }}
                className="grid grid-cols-[1.4fr_repeat(3,minmax(0,1fr))] items-center border-b border-white/6 px-6 py-5 text-sm text-muted last:border-b-0"
              >
                <div className="pr-4 text-white">{row.capability}</div>
                {row.values.map((value, itemIndex) => (
                  <div key={`${row.capability}-${itemIndex}`} className="flex justify-center">
                    {value ? (
                      <span className="flex h-9 w-9 items-center justify-center rounded-full bg-electric-400/15 text-electric-400">
                        <Check className="h-4 w-4" />
                      </span>
                    ) : (
                      <span className="flex h-9 w-9 items-center justify-center rounded-full bg-white/5 text-muted">
                        <Minus className="h-4 w-4" />
                      </span>
                    )}
                  </div>
                ))}
              </motion.div>
            ))}
          </div>
        </GlassCard>
      </Reveal>
    </section>
  );
}
