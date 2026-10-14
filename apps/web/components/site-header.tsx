import Link from "next/link";
import { ArrowRight, Languages } from "lucide-react";
import { GithubIcon } from "./icons";
import { site } from "@/lib/site";
import type { Dictionary, Locale } from "@/app/[lang]/dictionaries";

export function SiteHeader({ dict, lang, path = "" }: { dict: Dictionary; lang: Locale; path?: string }) {
  const other = lang === "pt" ? "en" : "pt";
  return (
    <header className="sticky top-0 z-40 border-b border-white/5 bg-ink-950/70 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-5">
        <Link href={`/${lang}`} className="group flex items-center gap-2.5">
          <span className="relative grid h-8 w-8 place-items-center overflow-hidden rounded-full">
            <span className="absolute inset-0 bg-[conic-gradient(from_0deg,#7c5cff,#22d3ee,#f472b6,#7c5cff)] blur-[2px] transition-transform duration-700 group-hover:rotate-180" />
            <span className="relative h-3 w-3 rounded-full bg-white/90" />
          </span>
          <span className="font-semibold tracking-tight">
            Tiago <span className="text-iris-300">AI</span>
          </span>
        </Link>
        <nav className="flex items-center gap-1 text-sm text-mist-300">
          <a
            href={site.repo}
            target="_blank"
            rel="noreferrer"
            className="hidden items-center gap-2 rounded-lg px-3 py-2 transition hover:bg-white/5 hover:text-white sm:flex"
          >
            <GithubIcon className="h-4 w-4" /> {dict.nav.github}
          </a>
          <a
            href={site.portfolio}
            target="_blank"
            rel="noreferrer"
            className="hidden rounded-lg px-3 py-2 transition hover:bg-white/5 hover:text-white md:block"
          >
            {dict.nav.website}
          </a>
          <Link
            href={`/${other}${path}`}
            className="flex items-center gap-1.5 rounded-lg px-3 py-2 transition hover:bg-white/5 hover:text-white"
            aria-label={dict.nav.language}
          >
            <Languages className="h-4 w-4" />
            <span className="uppercase">{other}</span>
          </Link>
          {path !== "/interview" && (
            <Link
              href={`/${lang}/interview`}
              className="ml-2 flex items-center gap-1.5 rounded-lg bg-white px-3.5 py-2 font-medium text-ink-950 transition hover:bg-iris-300"
            >
              {dict.nav.interview} <ArrowRight className="h-4 w-4" />
            </Link>
          )}
        </nav>
      </div>
    </header>
  );
}
