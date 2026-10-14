import type { Metadata } from "next";
import { Suspense } from "react";
import { getDictionary, getLocale } from "../dictionaries";
import { Interview } from "@/components/interview/interview";

export async function generateMetadata(): Promise<Metadata> {
  const dict = await getDictionary();
  return { title: `${dict.interview.title} · Tiago AI`, robots: { index: false } };
}

export default async function EmbedPage() {
  const dict = await getDictionary();
  const lang = await getLocale();
  return (
    <Suspense>
      <Interview dict={dict.interview} lang={lang} channel="widget" embedded />
    </Suspense>
  );
}
