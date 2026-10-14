import type { Metadata } from "next";
import { Suspense } from "react";
import { getDictionary, getLocale } from "../dictionaries";
import { SiteHeader } from "@/components/site-header";
import { Interview } from "@/components/interview/interview";
import { InterviewSkeleton } from "@/components/interview/interview-skeleton";

export async function generateMetadata(): Promise<Metadata> {
  const dict = await getDictionary();
  return { title: `${dict.interview.title} · Tiago AI` };
}

export default async function InterviewPage() {
  const dict = await getDictionary();
  const lang = await getLocale();
  return (
    <div className="relative min-h-dvh overflow-hidden">
      <div className="pointer-events-none absolute inset-0 -z-10">
        <div className="animate-aurora absolute -left-1/3 -top-1/2 h-[70vh] w-[70vw] rounded-full bg-iris-600/15 blur-[140px]" />
      </div>
      <SiteHeader dict={dict} lang={lang} path="/interview" />
      <Suspense fallback={<InterviewSkeleton />}>
        <Interview dict={dict.interview} lang={lang} />
      </Suspense>
    </div>
  );
}
