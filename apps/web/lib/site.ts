export const site = {
  repo: "https://github.com/Tiagokochem/tiago-ai-twin",
  portfolio: "https://tiagokochemsite.vercel.app/",
  github: "https://github.com/Tiagokochem",
  /** WhatsApp number (digits) of the Tiago AI bot (Evolution API). */
  whatsappBot: (process.env.NEXT_PUBLIC_WHATSAPP_BOT_NUMBER ?? "").replace(/\D/g, ""),
};

export function whatsappLink(number: string, text?: string): string {
  const query = text ? `?text=${encodeURIComponent(text)}` : "";
  return `https://wa.me/${number}${query}`;
}
