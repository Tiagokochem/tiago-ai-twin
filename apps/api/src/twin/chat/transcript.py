from twin.db.models import ChatSession
from twin.persona import Persona


def render_markdown(session: ChatSession, persona: Persona) -> str:
    pt = session.lang == "pt"
    title = "Entrevista com" if pt else "Interview with"
    you = "Recrutador" if pt else "Recruiter"
    sources = "Fontes" if pt else "Sources"
    lines = [
        f"# {title} {persona.short_name} AI",
        "",
        f"- Data: {session.created_at:%Y-%m-%d %H:%M} UTC"
        if pt
        else f"- Date: {session.created_at:%Y-%m-%d %H:%M} UTC",
        f"- {persona.name}: {persona.website}",
        f"- Contato: {persona.owner_contact_link}"
        if pt
        else f"- Contact: {persona.owner_contact_link}",
        "",
    ]
    for message in session.messages:
        speaker = you if message.role == "user" else f"{persona.short_name} AI"
        lines += [f"**{speaker}:**", "", message.content, ""]
        if message.citations:
            refs = ", ".join(f"[{c['n']}] {c['title']} > {c['heading']}" for c in message.citations)
            lines += [f"_{sources}: {refs}_", ""]
    return "\n".join(lines).rstrip() + "\n"
