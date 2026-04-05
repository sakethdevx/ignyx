"use client";
import { AnimatePresence, motion } from "framer-motion";
import { Search, TerminalSquare } from "lucide-react";
import { useState } from "react";

import { Reveal } from "@/components/landing/reveal";
import { SectionHeading } from "@/components/landing/section-heading";
import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/glass-card";
import { marketingDocsHref } from "@/lib/site";

const docsPreviewItems = [
  {
    label: "Quickstart",
    href: marketingDocsHref("/quickstart/"),
    title: "Quickstart in under five minutes",
    description:
      "Install Ignyx, define your first route, and ship a framework that already thinks about validation, docs, performance, and deployment as part of the same story.",
    snippetLabel: "Quickstart snippet",
    code: `from ignyx import Ignyx

app = Ignyx()

@app.get("/")
async def root():
    return {"message": "Hello from Ignyx"}

app.run(host="0.0.0.0", port=8000)`,
  },
  {
    label: "Routing",
    href: marketingDocsHref("/routing/"),
    title: "Routing that stays readable as the app grows",
    description:
      "Model expressive routes, typed parameters, and grouped routers without sacrificing clarity when your service surface area expands.",
    snippetLabel: "Routing snippet",
    code: `from ignyx import Ignyx, Router

app = Ignyx()
users = Router(prefix="/users")

@users.get("/{id}")
async def get_user(id: int):
    return {"id": id}

app.include_router(users)`,
  },
  {
    label: "Requests",
    href: marketingDocsHref("/request/"),
    title: "Request handling built for real application flows",
    description:
      "Access headers, params, cookies, and body helpers through a request object that keeps the day-to-day API straightforward.",
    snippetLabel: "Request snippet",
    code: `from ignyx import Ignyx, Request

app = Ignyx()

@app.post("/inspect")
async def inspect_request(request: Request):
    return {
        "method": request.method,
        "agent": request.headers.get("user-agent"),
    }`,
  },
  {
    label: "Middleware",
    href: marketingDocsHref("/middleware/"),
    title: "Middleware with enough structure for platform teams",
    description:
      "Add logging, CORS, session handling, and custom request lifecycle hooks in a way that remains understandable across a team.",
    snippetLabel: "Middleware snippet",
    code: `from ignyx import Ignyx
from ignyx.middleware import CORSMiddleware, GZipMiddleware

app = Ignyx()
app.add_middleware(CORSMiddleware(allow_origins=["*"]))
app.add_middleware(GZipMiddleware(minimum_size=512))`,
  },
  {
    label: "Validation",
    href: marketingDocsHref("/validation/"),
    title: "Validation that fits naturally into Python workflows",
    description:
      "Use typed request bodies and Pydantic-powered models to keep edge validation close to the handler and easy to reason about.",
    snippetLabel: "Validation snippet",
    code: `from ignyx import Ignyx
from pydantic import BaseModel

app = Ignyx()

class CreateUser(BaseModel):
    name: str
    plan: str

@app.post("/users")
async def create_user(body: CreateUser):
    return body.model_dump()`,
  },
  {
    label: "Security",
    href: marketingDocsHref("/security/"),
    title: "Security primitives ready for production APIs",
    description:
      "Layer auth and request guards into your routes without obscuring handler logic or overcomplicating common patterns.",
    snippetLabel: "Security snippet",
    code: `from ignyx import Ignyx, Depends
from ignyx.security import JWTBearer

app = Ignyx()
auth = JWTBearer(secret_key="change-me")

@app.get("/profile")
async def profile(user = Depends(auth)):
    return {"user": user}`,
  },
  {
    label: "Deployment",
    href: marketingDocsHref("/deployment/"),
    title: "A deployment story shaped for serious environments",
    description:
      "Run Ignyx with a clear operational model, lean runtime assumptions, and enough control to fit modern cloud and internal platform setups.",
    snippetLabel: "Deployment snippet",
    code: `from ignyx import Ignyx

app = Ignyx()

@app.get("/health")
async def health():
    return {"status": "ok"}

app.run(host="0.0.0.0", port=8000)`,
  },
];

export function DocsPreviewSection() {
  const [activeItem, setActiveItem] = useState(docsPreviewItems[0]);

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
              <a
                href={marketingDocsHref()}
                className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-muted transition-colors hover:border-electric-400/30 hover:bg-white/[0.07] hover:text-white"
              >
                <Search className="h-4 w-4" />
                Search docs
              </a>
              <div className="mt-6 space-y-2">
                {docsPreviewItems.map((item) => (
                  <button
                    key={item.label}
                    type="button"
                    onClick={() => setActiveItem(item)}
                    className={`block w-full rounded-2xl px-4 py-3 text-left text-sm transition-colors ${
                      activeItem.label === item.label
                        ? "bg-electric-400/12 text-white"
                        : "text-muted hover:bg-white/[0.05] hover:text-white"
                    }`}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </aside>

            <div className="p-6 sm:p-8">
              <AnimatePresence mode="wait">
                <motion.div
                  key={activeItem.label}
                  initial={{ opacity: 0, y: 16 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -12 }}
                  transition={{ duration: 0.28, ease: "easeOut" }}
                >
                  <div className="flex items-center gap-3 text-sm text-electric-400">
                    <TerminalSquare className="h-4 w-4" />
                    Documentation preview
                  </div>
                  <h3 className="mt-4 text-3xl font-semibold text-white">{activeItem.title}</h3>
                  <p className="mt-4 max-w-2xl text-sm leading-7 text-muted">
                    {activeItem.description}
                  </p>
                  <div className="mt-6">
                    <Button asChild variant="secondary">
                      <a href={activeItem.href}>Open full documentation</a>
                    </Button>
                  </div>

                  <div className="mt-8 rounded-[28px] border border-white/10 bg-[#07111d] p-5">
                    <div className="flex items-center gap-2 text-xs uppercase tracking-[0.26em] text-muted">
                      {activeItem.snippetLabel}
                    </div>
                    <pre className="mt-4 overflow-x-auto font-mono text-sm leading-7 text-slate-200">
                      {activeItem.code}
                    </pre>
                  </div>
                </motion.div>
              </AnimatePresence>
            </div>
          </div>
        </GlassCard>
      </Reveal>
    </section>
  );
}
