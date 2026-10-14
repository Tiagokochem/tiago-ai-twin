import re
import unicodedata

# Cheap first line of defense; the router LLM also classifies injections.
_INJECTION_PATTERNS = [
    r"ignore (all |any )?(the )?(previous|prior|above) (instructions|rules|prompts?)",
    r"disregard (all |any )?(the )?(previous|prior|above|your) (instructions|rules)",
    r"(reveal|show|print|repeat|leak) (me )?(your|the) (system |initial )?(prompt|instructions)",
    r"\bsystem prompt\b",
    r"\b(developer|dan|jailbreak) mode\b",
    r"you are (now|no longer)\b",
    r"ignore (todas )?(as )?(instrucoes|regras) (anteriores|acima)",
    r"esqueca (todas )?(as )?(instrucoes|regras)",
    r"(mostre|revele|repita|imprima) (o |seu |o seu )?(prompt|instrucoes)( do sistema)?",
    r"prompt do sistema",
    r"(voce agora e|a partir de agora voce e|finja que voce e)",
]
_COMPILED = [re.compile(p) for p in _INJECTION_PATTERNS]


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def looks_like_injection(text: str) -> bool:
    normalized = _normalize(text)
    return any(p.search(normalized) for p in _COMPILED)
