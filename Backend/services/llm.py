
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from core import config

logger = logging.getLogger("safezone.llm")

DEFAULT_TIMEOUT_S = 15


class LLMUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class Provider:

    name: str
    base_url: Optional[str]
    default_model: str


PROVIDERS: Dict[str, Provider] = {
    "deepseek": Provider(
        name="deepseek",
        base_url="https://api.deepseek.com/v1",
        default_model="deepseek-chat",
    ),
    "groq": Provider(
        name="groq",
        base_url="https://api.groq.com/openai/v1",
        default_model="llama-3.3-70b-versatile",
    ),
    "gemini": Provider(
        name="gemini",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        default_model="gemini-flash-latest",
    ),
    "openai": Provider(name="openai", base_url=None, default_model="gpt-4o-mini"),
    "openrouter": Provider(
        name="openrouter",
        base_url="https://openrouter.ai/api/v1",
        default_model="openai/gpt-4o-mini",
    ),
}


def credentials(name: str) -> tuple[str, str]:
    provider = PROVIDERS.get(name)
    if provider is None:
        return "", ""

    prefix = name.upper()
    api_key = (getattr(config, f"{prefix}_API_KEY", "") or "").strip()
    model = (getattr(config, f"{prefix}_MODEL", "") or "").strip()

    if config.LLM_PROVIDER == name:
        api_key = api_key or config.LLM_API_KEY
        model = model or config.LLM_MODEL

    if not api_key:
        return "", ""
    return api_key, model or provider.default_model


def provider_chain() -> List[Provider]:
    chain: List[Provider] = []
    for name in config.LLM_PROVIDERS:
        provider = PROVIDERS.get(name)
        if provider is None:
            logger.warning("Unknown LLM provider %r in LLM_PROVIDERS; skipping", name)
            continue
        api_key, _model = credentials(name)
        if not api_key:
            continue
        chain.append(provider)
    return chain


def available() -> bool:
    return bool(provider_chain())


def complete_json(
    system_prompt: str,
    user_prompt: str,
    *,
    timeout: int = DEFAULT_TIMEOUT_S,
) -> Dict[str, Any]:
    chain = provider_chain()
    if not chain:
        raise LLMUnavailable(
            "No LLM provider is configured. Set one of DEEPSEEK_API_KEY, "
            "GROQ_API_KEY or GEMINI_API_KEY, or LLM_API_KEY with LLM_PROVIDER."
        )

    failures: List[str] = []
    for provider in chain:
        api_key, model = credentials(provider.name)
        try:
            content = _chat(provider, api_key, model, system_prompt, user_prompt, timeout)
            parsed = json.loads(content)
        except Exception as exc:
            logger.warning("LLM provider %s failed: %s", provider.name, exc)
            failures.append(f"{provider.name}: {exc}")
            continue

        if not isinstance(parsed, dict):
            logger.warning("LLM provider %s returned %s, not an object", provider.name, type(parsed).__name__)
            failures.append(f"{provider.name}: response was not a JSON object")
            continue

        logger.info("LLM extraction served by %s (%s)", provider.name, model)
        return parsed

    raise LLMUnavailable("Every LLM provider failed -- " + "; ".join(failures))


def _chat(
    provider: Provider,
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    timeout: int,
) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=provider.base_url)
    response = client.chat.completions.create(
        model=model,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        timeout=timeout,
    )

    content = response.choices[0].message.content
    if not content:
        raise ValueError("empty response")
    return content


def complete_chat(
    messages: List[Dict[str, Any]],
    *,
    temperature: float = 0.3,
    max_tokens: int = 500,
    timeout: int = DEFAULT_TIMEOUT_S,
    provider: Optional[str] = None,
    api_key: str = "",
    model: str = "",
) -> str:
    if api_key and provider:
        pinned = PROVIDERS.get(provider)
        if pinned is None:
            raise LLMUnavailable(f"Unknown provider {provider!r}")
        chain = [pinned]
        overrides: Dict[str, tuple[str, str]] = {
            pinned.name: (api_key, model or pinned.default_model)
        }
    else:
        chain = provider_chain()
        overrides = {}

    if not chain:
        raise LLMUnavailable(
            "No LLM provider is configured. Set one of DEEPSEEK_API_KEY, "
            "GROQ_API_KEY or GEMINI_API_KEY, or LLM_API_KEY with LLM_PROVIDER."
        )

    failures: List[str] = []
    for candidate in chain:
        key, name = overrides.get(candidate.name) or credentials(candidate.name)
        try:
            from openai import OpenAI

            client = OpenAI(api_key=key, base_url=candidate.base_url)
            response = client.chat.completions.create(
                model=name,
                temperature=temperature,
                max_tokens=max_tokens,
                messages=messages,
                timeout=timeout,
            )
            content = (response.choices[0].message.content or "").strip()
        except Exception as exc:
            logger.warning("LLM provider %s failed: %s", candidate.name, exc)
            failures.append(f"{candidate.name}: {exc}")
            continue

        if not content:
            failures.append(f"{candidate.name}: empty response")
            continue

        logger.info("Chat served by %s (%s)", candidate.name, name)
        return content

    raise LLMUnavailable("Every LLM provider failed -- " + "; ".join(failures))
