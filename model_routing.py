"""Stable model routing; account metadata is not a generation guarantee."""

SUPPORTED_MODELS = ("gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-2.5-flash")


def available_supported_models(models):
    discovered = set()
    for model in models:
        name = (getattr(model, "name", None) or "").removeprefix("models/")
        actions = getattr(model, "supported_actions", None)
        if actions is None:
            actions = getattr(model, "supported_generation_methods", None)
        if name in SUPPORTED_MODELS and (not actions or "generateContent" in actions):
            discovered.add(name)
    return [model for model in SUPPORTED_MODELS if model in discovered]


def generation_candidates(primary, available):
    allowed = set(available).intersection(SUPPORTED_MODELS)
    return list(dict.fromkeys(model for model in (primary, *SUPPORTED_MODELS)
                             if model in allowed))
