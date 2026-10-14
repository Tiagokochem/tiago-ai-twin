import type { Metadata } from "next";
import { Suspense } from "react";
import { getDictionary, getLocale } from "../dictionaries";
import { Interview } from "@/components/interview/interview";
import { InterviewSkeleton } from "@/components/interview/interview-skeleton";

export async function generateMetadata(): Promise<Metadata> {
  const dict = await getDictionary();
  return { title: `${dict.interview.title} · Tiago AI`, robots: { index: false } };
}

export default async function EmbedPage() {
  const dict = await getDictionary();
  const lang = await getLocale();
  return (
    <Suspense fallback={<InterviewSkeleton embedded />}>
      <Interview dict={dict.interview} lang={lang} channel="widget" embedded />
    </Suspense>
  );
}
