"use client";

import { motion } from "framer-motion";
import {
  Blocks,
  Gauge,
  Network,
  ShieldCheck,
  Sparkles,
  Workflow,
} from "lucide-react";

import { Reveal } from "@/components/landing/reveal";
import { SectionHeading } from "@/components/landing/section-heading";
import { GlassCard } from "@/components/ui/glass-card";

const features = [
  {
    icon: Gauge,
    title: "High Performance",
    description: "Move request handling into a Rust engine that keeps Python ergonomics while cutting overhead from the hot path.",
  },
  {
    icon: Blocks,
    title: "Modular Architecture",
    description: "Compose routers, middleware, security, validation, and background workflows without framework sprawl.",
  },
  {
    icon: Workflow,
    title: "Async Support",
    description: "Build streaming APIs, WebSockets, and high-concurrency services with native async patterns that stay readable.",
  },
  {
    icon: Sparkles,
    title: "Developer Friendly",
    description: "FastAPI-like decorators, typed request handling, OpenAPI generation, and a workflow designed for teams shipping often.",
  },
  {
    icon: Network,
    title: "Observability Ready",
    description: "Trace request lifecycles, compare routing and Python execution time, and plug into modern telemetry pipelines.",
  },
  {
    icon: ShieldCheck,
    title: "Enterprise Posture",
    description: "Sessions, security primitives, stable routing, and a surface area shaped for production systems instead of toy demos.",
  },
];

export function FeaturesSection() {
  return (
    <section id="features" className="container py-24 sm:py-28">
      <Reveal>
        <SectionHeading
          eyebrow="Features"
          title="Built for teams that need speed, clarity, and operational confidence"
          description="Every section of Ignyx is meant to reduce friction: less glue code, fewer abstractions in your way, and a runtime story that scales with the product."
          align="center"
        />
      </Reveal>

      <div className="mt-14 grid gap-5 md:grid-cols-2 xl:grid-cols-3">
        {features.map((feature, index) => (
          <Reveal key={feature.title} delay={index * 0.06}>
            <motion.div whileHover={{ y: -8 }}>
              <GlassCard className="h-full rounded-[30px] border-white/10 bg-white/[0.04]">
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-electric-400/25 to-violet-500/25 text-electric-400">
                  <feature.icon className="h-6 w-6" />
                </div>
                <h3 className="mt-6 text-xl font-semibold text-white">{feature.title}</h3>
                <p className="mt-3 text-sm leading-7 text-muted">{feature.description}</p>
              </GlassCard>
            </motion.div>
          </Reveal>
        ))}
      </div>
    </section>
  );
}
