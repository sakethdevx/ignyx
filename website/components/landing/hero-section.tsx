"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import {
  ArrowRight,
  Orbit,
  Rocket,
  Sparkles,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { Reveal } from "@/components/landing/reveal";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/glass-card";
import { marketingDocsHref } from "@/lib/site";

const typingFrames = [
  "pip install ignyx",
  "app = Ignyx()",
  '@app.get("/health")',
  'return {"status": "green"}',
];

const metrics = [
  { label: "Request pipeline", value: "Native Rust core" },
  { label: "Developer experience", value: "FastAPI-like ergonomics" },
  { label: "Scale target", value: "APIs, AI systems, enterprise apps" },
];

export function HeroSection() {
  const fullText = useMemo(() => typingFrames.join("\n"), []);
  const [typed, setTyped] = useState("");

  useEffect(() => {
    let index = 0;
    const timer = setInterval(() => {
      setTyped(fullText.slice(0, index + 1));
      index += 1;
      if (index >= fullText.length) {
        clearInterval(timer);
      }
    }, 36);
    return () => clearInterval(timer);
  }, [fullText]);

  return (
    <section className="relative isolate overflow-hidden">
      <div className="hero-grid absolute inset-0 opacity-30" />
      <div className="absolute inset-x-0 top-0 h-[680px] bg-radial-glow" />
      <motion.div
        className="absolute left-[8%] top-28 h-40 w-40 rounded-full bg-electric-400/20 blur-[80px]"
        animate={{ y: [0, -25, 0], opacity: [0.45, 0.8, 0.45] }}
        transition={{ duration: 9, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="absolute right-[6%] top-40 h-48 w-48 rounded-full bg-violet-500/20 blur-[90px]"
        animate={{ y: [0, 30, 0], x: [0, -12, 0] }}
        transition={{ duration: 10, repeat: Infinity, ease: "easeInOut" }}
      />

      <div className="container relative z-10 pb-24 pt-20 sm:pb-28 sm:pt-24 lg:pb-32">
        <div className="grid items-center gap-14 lg:grid-cols-[1.15fr_0.85fr]">
          <div>
            <Reveal>
              <Badge className="bg-white/6 text-white">Enterprise release · Observability ready</Badge>
            </Reveal>
            <Reveal delay={0.08}>
              <h1 className="mt-8 max-w-4xl text-5xl font-semibold leading-[1.02] tracking-tight text-white sm:text-6xl lg:text-7xl">
                The Next-Gen Python Framework for Scalable Applications
              </h1>
            </Reveal>
            <Reveal delay={0.14}>
              <p className="mt-6 max-w-2xl text-lg leading-8 text-muted sm:text-xl">
                Ignyx gives Python teams a framework that feels ergonomic on day one and operationally serious on day one hundred, with a Rust-powered request core built for modern APIs, AI workloads, and enterprise systems.
              </p>
            </Reveal>

            <Reveal delay={0.2}>
              <div className="mt-10 flex flex-col gap-4 sm:flex-row">
                <Button asChild size="lg">
                  <Link href="#getting-started">
                    Get Started
                    <ArrowRight className="h-4 w-4" />
                  </Link>
                </Button>
                <Button asChild size="lg" variant="secondary">
                  <Link href={marketingDocsHref()}>View Docs</Link>
                </Button>
              </div>
            </Reveal>

            <Reveal delay={0.28}>
              <div className="mt-12 grid gap-4 sm:grid-cols-3">
                {metrics.map((metric) => (
                  <GlassCard key={metric.label} className="rounded-3xl bg-white/[0.04] p-4">
                    <p className="text-sm text-muted">{metric.label}</p>
                    <p className="mt-2 text-sm font-medium text-white">{metric.value}</p>
                  </GlassCard>
                ))}
              </div>
            </Reveal>
          </div>

          <Reveal delay={0.18} className="relative">
            <GlassCard className="panel-line overflow-hidden rounded-[32px] border-white/12 p-0">
              <div className="border-b border-white/10 bg-white/[0.04] px-5 py-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="h-3 w-3 rounded-full bg-[#ff5f57]" />
                    <span className="h-3 w-3 rounded-full bg-[#febc2e]" />
                    <span className="h-3 w-3 rounded-full bg-[#28c840]" />
                  </div>
                  <div className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-muted">
                    launch.py
                  </div>
                </div>
              </div>

              <div className="relative px-5 py-6">
                <div className="absolute inset-0 bg-gradient-to-br from-electric-400/10 via-transparent to-violet-500/10" />
                <pre className="relative min-h-[280px] overflow-hidden rounded-[24px] bg-[#08101c] p-6 font-mono text-sm leading-7 text-slate-100 shadow-inner">
                  <span className="text-electric-400">from</span> ignyx <span className="text-electric-400">import</span> Ignyx{"\n\n"}
                  <span className="text-slate-400">{typed}</span>
                  <span className="ml-0.5 inline-block h-5 w-2 animate-pulse rounded bg-electric-400 align-middle" />
                </pre>

                <div className="relative mt-5 grid gap-3 sm:grid-cols-3">
                  {[
                    { icon: Rocket, label: "Fast paths", value: "Hyper + Tokio" },
                    { icon: Orbit, label: "Tracing", value: "Request spans" },
                    { icon: Sparkles, label: "Zero-copy", value: "Streamed uploads" },
                  ].map((item) => (
                    <motion.div
                      key={item.label}
                      whileHover={{ y: -4, scale: 1.01 }}
                      className="rounded-3xl border border-white/10 bg-white/[0.04] p-4"
                    >
                      <item.icon className="h-5 w-5 text-electric-400" />
                      <div className="mt-3 text-sm font-medium text-white">{item.label}</div>
                      <div className="mt-1 text-sm text-muted">{item.value}</div>
                    </motion.div>
                  ))}
                </div>
              </div>
            </GlassCard>
          </Reveal>
        </div>
      </div>
    </section>
  );
}
