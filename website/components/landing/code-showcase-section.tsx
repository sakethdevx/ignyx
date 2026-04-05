"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useState } from "react";

import { Reveal } from "@/components/landing/reveal";
import { SectionHeading } from "@/components/landing/section-heading";
import { GlassCard } from "@/components/ui/glass-card";

const codeTabs = [
  {
    label: "API",
    eyebrow: "Python API",
    title: "Readable on the surface, serious underneath",
    description:
      "Define routes the way Python developers expect while the runtime keeps the transport layer efficient and production-minded.",
    code: `from ignyx import Ignyx, JSONResponse\n\napp = Ignyx(title=\"Ignyx Platform\")\n\n@app.get(\"/v1/health\")\nasync def health():\n    return JSONResponse({\"status\": \"green\", \"service\": \"api\"})\n\n@app.post(\"/v1/inference\")\nasync def infer(body: dict):\n    return {\"accepted\": True, \"trace\": body.get(\"trace_id\")}`,
  },
  {
    label: "CLI",
    eyebrow: "DX Workflow",
    title: "From install to running service in minutes",
    description:
      "Ignyx is built for teams that want to move quickly without giving up clean local workflows or production alignment.",
    code: `uv add ignyx\n\nignyx new launchpad-api\ncd launchpad-api\npython app.py\n\n# docs, routing, validation, and performance-ready defaults\n# without needing an ASGI stack to feel complete`,
  },
  {
    label: "Example",
    eyebrow: "Practical Patterns",
    title: "Great for AI endpoints, internal tools, and platform APIs",
    description:
      "Keep business logic explicit while still getting typed inputs, dependency resolution, sessions, and native performance benefits.",
    code: `from ignyx import Depends, Ignyx, UploadFile\n\napp = Ignyx()\n\ndef current_workspace():\n    return {\"region\": \"us-east\", \"plan\": \"enterprise\"}\n\n@app.post(\"/assets\")\nasync def upload_asset(file: UploadFile, workspace = Depends(current_workspace)):\n    payload = await file.read()\n    return {\"size\": len(payload), \"workspace\": workspace[\"plan\"]}`,
  },
];

export function CodeShowcaseSection() {
  const [activeTab, setActiveTab] = useState(codeTabs[0]);

  return (
    <section className="container py-24 sm:py-28">
      <div className="grid gap-10 lg:grid-cols-[0.9fr_1.1fr] lg:items-end">
        <Reveal>
          <SectionHeading
            eyebrow="Code Showcase"
            title="A code experience that feels fast before you benchmark it"
            description="The website should tell the story, but the code needs to close the deal. Ignyx keeps the API surface clean while surfacing the pieces teams care about when systems get real."
          />
        </Reveal>

        <Reveal delay={0.08}>
          <div className="flex flex-wrap gap-3">
            {codeTabs.map((tab) => (
              <button
                key={tab.label}
                type="button"
                onClick={() => setActiveTab(tab)}
                className={`rounded-full px-4 py-2 text-sm transition-all duration-300 ${
                  activeTab.label === tab.label
                    ? "bg-white text-slate-950 shadow-glow"
                    : "border border-white/10 bg-white/[0.04] text-muted hover:text-white"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </Reveal>
      </div>

      <div className="mt-10 grid gap-6 lg:grid-cols-[0.42fr_0.58fr]">
        <Reveal>
          <GlassCard className="rounded-[30px]">
            <p className="text-sm uppercase tracking-[0.28em] text-electric-400">
              {activeTab.eyebrow}
            </p>
            <h3 className="mt-4 text-2xl font-semibold text-white">{activeTab.title}</h3>
            <p className="mt-4 text-sm leading-7 text-muted">{activeTab.description}</p>
          </GlassCard>
        </Reveal>

        <Reveal delay={0.08}>
          <GlassCard className="overflow-hidden rounded-[30px] p-0">
            <div className="flex items-center justify-between border-b border-white/10 bg-white/[0.04] px-5 py-4">
              <div className="text-sm text-muted">ignyx://showcase/{activeTab.label.toLowerCase()}</div>
              <div className="rounded-full border border-white/10 px-3 py-1 text-xs text-muted">
                Live preview
              </div>
            </div>
            <div className="min-h-[360px] bg-[#07111d] p-6">
              <AnimatePresence mode="wait">
                <motion.pre
                  key={activeTab.label}
                  initial={{ opacity: 0, y: 14 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -12 }}
                  transition={{ duration: 0.35, ease: "easeOut" }}
                  className="overflow-x-auto font-mono text-sm leading-7 text-slate-200"
                >
                  {activeTab.code}
                </motion.pre>
              </AnimatePresence>
            </div>
          </GlassCard>
        </Reveal>
      </div>
    </section>
  );
}
