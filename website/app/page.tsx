import { CodeShowcaseSection } from "@/components/landing/code-showcase-section";
import { CtaSection } from "@/components/landing/cta-section";
import { CursorGlow } from "@/components/landing/cursor-glow";
import { DocsPreviewSection } from "@/components/landing/docs-preview-section";
import { FeaturesSection } from "@/components/landing/features-section";
import { GettingStartedSection } from "@/components/landing/getting-started-section";
import { HeroSection } from "@/components/landing/hero-section";
import { SiteFooter } from "@/components/landing/site-footer";
import { SiteHeader } from "@/components/landing/site-header";
import { UseCasesSection } from "@/components/landing/use-cases-section";
import { WhyIgnyxSection } from "@/components/landing/why-ignyx-section";

export default function HomePage() {
  return (
    <main className="relative overflow-hidden">
      <CursorGlow />
      <SiteHeader />
      <HeroSection />
      <FeaturesSection />
      <CodeShowcaseSection />
      <WhyIgnyxSection />
      <UseCasesSection />
      <GettingStartedSection />
      <DocsPreviewSection />
      <CtaSection />
      <SiteFooter />
    </main>
  );
}
