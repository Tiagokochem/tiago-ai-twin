import Link from "next/link";
import { ArrowRight, Briefcase, Mic, Sparkles } from "lucide-react";
import { getDictionary, getLocale } from "./dictionaries";
import { SiteHeader } from "@/components/site-header";
import { HeroVisual } from "@/components/landing/hero-visual";
import { AgentFlow } from "@/components/landing/agent-flow";
import { WhatsappIcon, GithubIcon } from "@/components/icons";
import { site, whatsappLink } from "@/lib/site";

const SAMPLE_QUESTIONS = {
  pt: [
    "Qual é a sua experiência com agentes de IA?",
    "Como você evita resgates duplicados?",
    "Quais marketplaces o Nuvartis integra?",
  ],
  en: [
    "What is your experience with AI agents?",
    "How do you prevent duplicate withdrawals?",
    "Which marketplaces does Nuvartis integrate?",
  ],
};

const STACK = ["Python", "FastAPI", "LangGraph", "pgvector", "OpenAI", "DeepSeek", "Next.js", "Docker"];

export default async function Home() {
  const dict = await getDictionary();
  const lang = await getLocale();

  return (
    <>
      <SiteHeader dict={dict} lang={lang} />
      <main className="relative overflow-hidden">
        <div className="pointer-events-none absolute inset-0 -z-10">
          <div className="grid-bg absolute inset-0" />
          <div className="animate-aurora absolute -left-1/4 -top-1/3 h-[70vh] w-[70vw] rounded-full bg-iris-600/20 blur-[120px]" />
          <div className="animate-aurora absolute -right-1/4 top-1/4 h-[50vh] w-[50vw] rounded-full bg-cyan-glow/10 blur-[120px] [animation-delay:-6s]" />
        </div>

        <section className="mx-auto grid max-w-6xl items-center gap-12 px-5 pb-20 pt-14 lg:grid-cols-[1.1fr_1fr] lg:pt-24">
          <div>
            <span className="inline-flex items-center gap-2 rounded-full border border-iris-400/30 bg-iris-500/10 px-3 py-1 text-xs font-medium text-iris-300">
              <Sparkles className="h-3.5 w-3.5" /> {dict.hero.badge}
            </span>
            <h1 className="mt-6 text-4xl font-semibold leading-[1.05] tracking-tight sm:text-6xl">
              {dict.hero.title1}
              <br />
              <span className="text-gradient">{dict.hero.title2}</span>
            </h1>
            <p className="mt-6 max-w-xl text-lg leading-relaxed text-mist-300">{dict.hero.subtitle}</p>

            <div className="mt-9 flex flex-wrap items-center gap-3">
              <Link
                href={`/${lang}/interview`}
                className="group flex items-center gap-2 rounded-xl bg-white px-5 py-3 font-medium text-ink-950 shadow-[0_0_40px_-8px_rgba(149,125,255,0.8)] transition hover:bg-iris-300"
              >
                {dict.hero.ctaChat}
                <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" />
              </Link>
              <Link
                href={`/${lang}/interview?mode=voice`}
                className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-5 py-3 font-medium transition hover:border-white/20 hover:bg-white/10"
              >
                <Mic className="h-4 w-4 text-cyan-glow" /> {dict.hero.ctaVoice}
              </Link>
              <Link
                href={`/${lang}/interview?mode=jobfit`}
                className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-5 py-3 font-medium transition hover:border-white/20 hover:bg-white/10"
              >
                <Briefcase className="h-4 w-4 text-iris-300" /> {dict.hero.ctaJobFit}
              </Link>
            </div>

            {site.whatsappBot && (
              <a
                href={whatsappLink(site.whatsappBot, dict.interview.whatsapp.prefill)}
                target="_blank"
                rel="noreferrer"
                className="mt-5 inline-flex items-center gap-2 text-sm text-mist-300 transition hover:text-wa"
              >
                <WhatsappIcon className="h-4 w-4 text-wa" /> {dict.hero.ctaWhatsapp}
              </a>
            )}
            <p className="mt-6 max-w-lg text-sm text-mist-400">{dict.hero.note}</p>
          </div>

          <HeroVisual questions={SAMPLE_QUESTIONS[lang]} />
        </section>

        <section className="mx-auto max-w-6xl px-5 pb-24">
          <div className="grid gap-4 md:grid-cols-3">
            {dict.features.map((f) => (
              <div key={f.title} className="glass rounded-2xl p-6">
                <h3 className="text-lg font-semibold">{f.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-mist-300">{f.body}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-5 pb-24">
          <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">{dict.flow.title}</h2>
          <p className="mt-2 max-w-2xl text-mist-300">{dict.flow.subtitle}</p>
          <div className="mt-10">
            <AgentFlow steps={dict.flow.steps} />
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-5 pb-24">
          <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">{dict.engineering.title}</h2>
          <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {dict.engineering.items.map((item, i) => (
              <div key={item.title} className="rounded-2xl border border-white/5 bg-white/[0.02] p-5">
                <span className="font-mono text-xs text-iris-300">0{i + 1}</span>
                <h3 className="mt-2 font-semibold">{item.title}</h3>
                <p className="mt-1.5 text-sm leading-relaxed text-mist-300">{item.body}</p>
              </div>
            ))}
          </div>
          <div className="mt-8 flex flex-wrap gap-2">
            {STACK.map((tech) => (
              <span key={tech} className="rounded-full border border-white/10 px-3 py-1 font-mono text-xs text-mist-300">
                {tech}
              </span>
            ))}
          </div>
        </section>
      </main>

      <footer className="border-t border-white/5">
        <div className="mx-auto flex max-w-6xl flex-col gap-3 px-5 py-8 text-sm text-mist-400 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p>{dict.footer.built}</p>
            <p className="mt-1 text-xs">{dict.footer.disclaimer}</p>
          </div>
          <a href={site.repo} target="_blank" rel="noreferrer" className="flex items-center gap-2 hover:text-white">
            <GithubIcon className="h-4 w-4" /> tiago-ai-twin
          </a>
        </div>
      </footer>
    </>
  );
}
