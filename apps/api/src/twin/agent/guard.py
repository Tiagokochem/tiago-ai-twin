import re
import unicodedata

# Cheap first line of defense; the router LLM also classifies injections.
_INJECTION_PATTERNS = [
    r"ignore (all |any )?(the )?(previous|prior|above) (instructions|rules|prompts?)",
    r"disregard (all |any )?(the )?(previous|prior|above|your) (instructions|rules)",
    r"(ignore|forget|bypass) (all )?your (rules|instructions|guidelines)",
    r"(everything|all text|the text) (above|before) (this|my first)",
    r"(reveal|show|print|repeat|leak) (me )?(your|the) (system |initial )?(prompt|instructions)",
    r"\bsystem prompt\b",
    r"\b(developer|dan|jailbreak) mode\b",
    r"you are (now|no longer)\b",
    r"ignore (todas )?(as )?(instrucoes|regras) (anteriores|acima)",
    r"esqueca (todas )?(as )?(instrucoes|regras)",
    r"(mostre|revele|repita|imprima) (o |seu |o seu )?(prompt|instrucoes)( do sistema)?",
    r"prompt do sistema",
    r"(transcreva|repita|copie) (tudo|todo o texto) (o )?que (veio|foi dito|voce recebeu) antes",
    r"(texto|mensagens?|instrucoes) que (voce )?recebeu antes",
    r"(repeat|copy) (word for word|verbatim) (the|everything)",
    r"(voce agora e|a partir de agora voce e|finja que voce e)",
]
_COMPILED = [re.compile(p) for p in _INJECTION_PATTERNS]
# "i.g.n.o.r.e" / "i g n o r e": single letters joined by separators.
_SPELLED_OUT = re.compile(r"\b(?:[a-z][\s.\-_*]){3,}[a-z]\b")


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower())
    plain = "".join(c for c in decomposed if not unicodedata.combining(c))
    return _SPELLED_OUT.sub(lambda m: re.sub(r"[\s.\-_*]", "", m.group()), plain)


def looks_like_injection(text: str) -> bool:
    normalized = _normalize(text)
    return any(p.search(normalized) for p in _COMPILED)
