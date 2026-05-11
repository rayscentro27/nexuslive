from __future__ import annotations

HOOK_STYLES = (
    "curiosity",
    "contrarian",
    "mistake-based",
    "money-focused",
    "authority",
    "myth-busting",
)


def generate_hooks(topic: str, count: int = 10) -> list[dict]:
    topic = (topic or "").strip() or "business funding"
    templates = {
        "curiosity": "Nobody tells you this about {topic}.",
        "contrarian": "The advice you keep hearing about {topic} is probably backward.",
        "mistake-based": "You are probably making this {topic} mistake too early.",
        "money-focused": "This {topic} mistake can cost you more than you think.",
        "authority": "Here is what experienced operators check before they touch {topic}.",
        "myth-busting": "Myth: one quick fix solves {topic}. Reality is different.",
    }
    hooks = []
    styles = list(HOOK_STYLES)
    for idx in range(max(count, 1)):
        style = styles[idx % len(styles)]
        text = templates[style].format(topic=topic)
        hooks.append({"style": style, "hook": text})
    return hooks[:count]
