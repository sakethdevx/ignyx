"use client";

import { Bot, Building2, CloudLightning, Rocket } from "lucide-react";

import { Reveal } from "@/components/landing/reveal";
import { SectionHeading } from "@/components/landing/section-heading";
import { GlassCard } from "@/components/ui/glass-card";

const useCases = [
  {
    icon: Rocket,
    title: "Startup apps",
    description: "Ship product quickly with a familiar Python experience and a runtime that does not need a rewrite when traffic starts to matter.",
  },
  {
    icon: CloudLightning,
    title: "APIs",
    description: "Build public or internal APIs with clean schemas, predictable latency, and middleware primitives that fit platform teams.",
  },
  {
    icon: Bot,
    title: "AI/ML pipelines",
    description: "Support inference endpoints, ingestion services, and async workflows where throughput and readable code both matter.",
  },
  {
    icon: Building2,
    title: "Enterprise systems",
    description: "Use typed handlers, sessions, security layers, and observability hooks to fit into serious production environments.",
  },
];

export function UseCasesSection() {
  return (
    <section className="container py-24 sm:py-28">
      <Reveal>
        <SectionHeading
          eyebrow="Use Cases"
          title="Ignyx fits the teams building now and the teams scaling later"
          description="The same framework should feel sharp in a startup sprint and credible in a platform review. Ignyx is designed to cover that spread."
        />
      </Reveal>

      <div className="mt-12 grid gap-5 md:grid-cols-2 xl:grid-cols-4">
        {useCases.map((item, index) => (
          <Reveal key={item.title} delay={index * 0.06}>
            <GlassCard className="group h-full rounded-[28px]">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white/[0.05] text-electric-400 transition-transform duration-300 group-hover:scale-110">
                <item.icon className="h-6 w-6" />
              </div>
              <h3 className="mt-5 text-lg font-semibold text-white">{item.title}</h3>
              <p className="mt-3 text-sm leading-7 text-muted">{item.description}</p>
            </GlassCard>
          </Reveal>
        ))}
      </div>
    </section>
  );
}
