"use client";

import { Reveal } from "@/components/landing/reveal";
import { SectionHeading } from "@/components/landing/section-heading";
import { GlassCard } from "@/components/ui/glass-card";

const testimonials = [
  {
    quote:
      "Ignyx feels like the first Python framework we could hand to platform engineers without hearing concerns about the request path six weeks later.",
    name: "Maya Chen",
    role: "Staff Engineer, Northline AI",
  },
  {
    quote:
      "We wanted FastAPI-level clarity with a more opinionated production story. Ignyx landed in that space immediately.",
    name: "Jonas Mercer",
    role: "CTO, Array Cloud",
  },
  {
    quote:
      "The combination of Python ergonomics and Rust internals makes it much easier to defend architectural decisions to both product teams and ops teams.",
    name: "Priya Raman",
    role: "Principal Architect, Helio Systems",
  },
];

export function TestimonialsSection() {
  return (
    <section className="container py-24 sm:py-28">
      <Reveal>
        <SectionHeading
          eyebrow="Social Proof"
          title="Early signals from teams that care about performance and polish"
          description="Placeholder voices for now, but intentionally shaped like the kind of validation a premium developer platform should eventually earn."
          align="center"
        />
      </Reveal>

      <div className="mt-12 grid gap-5 lg:grid-cols-3">
        {testimonials.map((testimonial, index) => (
          <Reveal key={testimonial.name} delay={index * 0.08}>
            <GlassCard className="h-full rounded-[30px]">
              <p className="text-base leading-8 text-slate-100">“{testimonial.quote}”</p>
              <div className="mt-8 flex items-center gap-4">
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-br from-electric-400 to-violet-500 text-sm font-semibold text-white">
                  {testimonial.name
                    .split(" ")
                    .map((part) => part[0])
                    .join("")}
                </div>
                <div>
                  <div className="font-medium text-white">{testimonial.name}</div>
                  <div className="text-sm text-muted">{testimonial.role}</div>
                </div>
              </div>
            </GlassCard>
          </Reveal>
        ))}
      </div>
    </section>
  );
}
