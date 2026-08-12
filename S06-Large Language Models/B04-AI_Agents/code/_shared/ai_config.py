"""
ai_config.py -- shared multi-provider AI connection config for the
B04-AI_Agents notebooks.

Three ways to reach a model, selectable per-notebook:
    'gemini'    -- Google Gemini API (free tier via Google AI Studio)
    'bedrock'   -- Claude via AWS Bedrock (uses your AWS IAM credentials)
    'anthropic' -- Claude via the Anthropic API directly (console.anthropic.com)

All credentials and model names are read from a .env file at the repo root
(see .env.example for the full list of variables). Nothing here ever prints
or logs a raw key.

Usage from a notebook:

    import ai_config
    provider = ai_config.get_provider('gemini')   # or 'bedrock' / 'anthropic'
    ai_config.test_connection(provider)
    result = provider.generate('Say hello in five words.')
    print(result.text)
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


def _find_and_load_env() -> None:
    """
    Walk up from this file's own location looking for a .env at the repo
    root, and load it. Safe to call even if no .env exists yet (env vars
    might already be set some other way, e.g. shell export or CI secrets).
    """
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / ".env"
        if candidate.is_file():
            load_dotenv(candidate)
            return


_find_and_load_env()


class AIConnectionError(RuntimeError):
    """
    Raised for any provider misconfiguration or connection failure.
    Every raise site here includes a specific, actionable message (which
    variable is missing, which package to install, which URL to visit) --
    the goal is that you never have to read a raw SDK stack trace to know
    what to do next.
    """


@dataclass
class ProviderResult:
    text: str
    raw: object  # the underlying SDK response object, for notebooks that want more
    usage: dict  # normalized: input_tokens, output_tokens, cache_read_tokens,
    #             cache_write_tokens -- the latter two are None where a
    #             provider does not expose or support that concept for this
    #             call (see each provider's generate() for specifics).


class Provider:
    """Common interface every backend implements."""

    name: str
    model: str

    def generate(
        self, prompt: str, max_tokens: int = 200, system: Optional[str] = None
    ) -> ProviderResult:
        """
        Args:
            prompt: the user message.
            max_tokens: cap on generated output tokens.
            system: optional system/instruction text. When provided, the
                Anthropic and Bedrock providers mark it as a cache
                checkpoint (real prompt caching); Gemini accepts it as a
                system instruction but does NOT cache it this way -- Gemini
                caching requires a separate explicit CachedContent resource,
                which this shared client does not create.
        """
        raise NotImplementedError

    def get_raw_client(self):
        """
        Return the underlying vendor SDK client (a real `anthropic.Anthropic`,
        `anthropic.AnthropicBedrockMantle`, or `google.genai.Client`). The
        Anthropic and Bedrock clients share the exact same `.messages.create()`
        / `.messages.stream()` interface, so code written against one works
        unchanged against the other -- only construction differs.

        `.generate()` is deliberately a single-shot prompt-plus-system
        interface -- it has no `tools` parameter and no multi-turn message
        list, because normalizing tool-calling across three different wire
        formats (Anthropic tool_use/tool_result, Gemini function_call/
        function_response, Bedrock toolUse/toolResult) is real design work
        this module does not attempt yet. Any notebook that needs a full
        agent loop -- Chapter 2 onward -- drops down to the raw client via
        this method instead of waiting for that abstraction to exist.
        """
        return self._client


class GeminiProvider(Provider):
    name = "gemini"

    def __init__(self, model: Optional[str] = None):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise AIConnectionError(
                "GEMINI_API_KEY is not set. Add it to your .env file at the "
                "repo root (copy .env.example to .env first if you have not "
                "already). Get a free key at https://aistudio.google.com/app/apikey"
            )
        try:
            from google import genai
        except ImportError as exc:
            raise AIConnectionError(
                "The 'google-genai' package is not installed. Run: "
                "pip install google-genai"
            ) from exc

        self.model = model or os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
        self._client = genai.Client(api_key=api_key)

    def generate(
        self, prompt: str, max_tokens: int = 200, system: Optional[str] = None
    ) -> ProviderResult:
        try:
            from google.genai import types

            config = None
            if system is not None:
                # NOTE: this is a plain system instruction, not a cache.
                # Real Gemini caching needs an explicit CachedContent
                # resource (client.caches.create(...)) which this shared
                # client does not set up -- cache_read_tokens/
                # cache_write_tokens below will always be None for Gemini.
                config = types.GenerateContentConfig(system_instruction=system)

            response = self._client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=config,
            )
        except Exception as exc:
            raise AIConnectionError(
                f"Gemini request failed (model={self.model}): {exc}"
            ) from exc

        um = response.usage_metadata
        usage = {
            "input_tokens": getattr(um, "prompt_token_count", None),
            "output_tokens": getattr(um, "candidates_token_count", None),
            "cache_read_tokens": None,
            "cache_write_tokens": None,
        }
        return ProviderResult(text=response.text, raw=response, usage=usage)


class BedrockProvider(Provider):
    """
    Claude via AWS Bedrock, using Anthropic's own AnthropicBedrockMantle
    client -- NOT boto3's Converse API. Mantle speaks the exact same
    Messages API shape as direct Anthropic (tool_use/tool_result,
    snake_case stop_reason, cache_control) over AWS SigV4 auth, so code
    written against this provider's .generate() and .get_raw_client() reads
    identically to AnthropicProvider's -- there is no separate camelCase
    Converse API vocabulary (toolUse/toolResult/stopReason) to learn.
    """

    name = "bedrock"

    def __init__(self, model: Optional[str] = None):
        access_key = os.getenv("AWS_ACCESS_KEY_ID")
        secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION")

        missing = [
            var_name
            for var_name, value in [
                ("AWS_ACCESS_KEY_ID", access_key),
                ("AWS_SECRET_ACCESS_KEY", secret_key),
                ("AWS_REGION (or AWS_DEFAULT_REGION)", region),
            ]
            if not value
        ]
        if missing:
            raise AIConnectionError(
                "Missing AWS Bedrock config in .env: " + ", ".join(missing) +
                ". See .env.example for the full list of Bedrock variables."
            )
        try:
            from anthropic import AnthropicBedrockMantle
        except ImportError as exc:
            raise AIConnectionError(
                "The 'anthropic' package's Bedrock extra is not installed. "
                "Run: pip install \"anthropic[bedrock]\""
            ) from exc

        self.model = model or os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-sonnet-5")
        self._region = region
        self._client = AnthropicBedrockMantle(
            aws_access_key=access_key,
            aws_secret_key=secret_key,
            aws_region=region,
        )

    def generate(
        self, prompt: str, max_tokens: int = 200, system: Optional[str] = None
    ) -> ProviderResult:
        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system is not None:
            # Real ephemeral cache checkpoint, identical mechanics to
            # AnthropicProvider -- Mantle is the same Messages API.
            kwargs["system"] = [
                {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}
            ]

        try:
            response = self._client.messages.create(**kwargs)
        except Exception as exc:
            hint = ""
            low = str(exc).lower()
            if "on-demand" in low or "inference profile" in low:
                hint = (
                    " This model may require an inference-profile ID instead "
                    "of the bare model ID for your account/region -- check "
                    "the 'Cross-region inference' page in the AWS Bedrock console."
                )
            elif "access" in low and ("denied" in low or "not authorized" in low):
                hint = (
                    " Check that this model is 'Enabled' for your account under "
                    "Bedrock > Model access in the AWS console."
                )
            raise AIConnectionError(
                f"Bedrock request failed (model={self.model}, region={self._region}): "
                f"{exc}.{hint}"
            ) from exc

        u = response.usage
        usage = {
            "input_tokens": getattr(u, "input_tokens", None),
            "output_tokens": getattr(u, "output_tokens", None),
            "cache_read_tokens": getattr(u, "cache_read_input_tokens", None),
            "cache_write_tokens": getattr(u, "cache_creation_input_tokens", None),
        }
        return ProviderResult(text=response.content[0].text, raw=response, usage=usage)


class AnthropicProvider(Provider):
    name = "anthropic"

    def __init__(self, model: Optional[str] = None):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise AIConnectionError(
                "ANTHROPIC_API_KEY is not set. Add it to your .env file at the "
                "repo root. Note: a Claude Pro/Team CHAT subscription does NOT "
                "include API credit -- create a separate key (and add a small "
                "prepaid balance) at https://console.anthropic.com"
            )
        try:
            import anthropic
        except ImportError as exc:
            raise AIConnectionError(
                "The 'anthropic' package is not installed. Run: pip install anthropic"
            ) from exc

        self.model = model or os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")
        self._client = anthropic.Anthropic(api_key=api_key)

    def generate(
        self, prompt: str, max_tokens: int = 200, system: Optional[str] = None
    ) -> ProviderResult:
        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system is not None:
            # Real ephemeral cache checkpoint. Below the model's minimum
            # cacheable length, the call still succeeds -- cache_creation
            # and cache_read just both read 0.
            kwargs["system"] = [
                {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}
            ]

        try:
            response = self._client.messages.create(**kwargs)
        except Exception as exc:
            raise AIConnectionError(
                f"Anthropic request failed (model={self.model}): {exc}"
            ) from exc

        u = response.usage
        usage = {
            "input_tokens": getattr(u, "input_tokens", None),
            "output_tokens": getattr(u, "output_tokens", None),
            "cache_read_tokens": getattr(u, "cache_read_input_tokens", None),
            "cache_write_tokens": getattr(u, "cache_creation_input_tokens", None),
        }
        return ProviderResult(text=response.content[0].text, raw=response, usage=usage)


_PROVIDER_CLASSES = {
    "gemini": GeminiProvider,
    "bedrock": BedrockProvider,
    "anthropic": AnthropicProvider,
}


def get_provider(name: Optional[str] = None, model: Optional[str] = None) -> Provider:
    """
    Build a connected Provider for 'gemini', 'bedrock', or 'anthropic'.

    Args:
        name: which backend to use. If omitted, falls back to the
            AI_PROVIDER value in .env.
        model: override the provider's default model name (otherwise reads
            GEMINI_MODEL / BEDROCK_MODEL_ID / ANTHROPIC_MODEL from .env, or
            a hardcoded fallback).
    Returns:
        A connected Provider instance ready for .generate(prompt).
    Raises:
        AIConnectionError: on an unknown provider name, a missing
            credential, or a missing SDK package -- always with a specific,
            actionable message.
    """
    resolved_name = (name or os.getenv("AI_PROVIDER", "")).strip().lower()
    if resolved_name not in _PROVIDER_CLASSES:
        raise AIConnectionError(
            f"Unknown provider {resolved_name!r}. Choose one of: "
            f"{', '.join(_PROVIDER_CLASSES)} -- pass it to "
            "get_provider('...') or set AI_PROVIDER in .env."
        )
    return _PROVIDER_CLASSES[resolved_name](model=model)


def get_anthropic_reference_provider(model: Optional[str] = None) -> Provider:
    """
    Return a Provider guaranteed to be real Claude, for notebook sections
    that specifically teach or demonstrate Anthropic-only mechanics (tool_use
    blocks, stop_reason values, interleaved thinking, prompt-cache
    cache_control, etc.) rather than provider-agnostic concepts.

    Defaults to Bedrock + Claude Sonnet 5 -- this project's designated path
    to real Claude, since it does not hold a separately funded Anthropic
    Console API key (a Claude Pro/Team chat subscription does not include
    API credit; see AnthropicProvider's error message). Set
    ANTHROPIC_REFERENCE_MODEL in .env to override the model id.

    Args:
        model: override the model id (otherwise reads
            ANTHROPIC_REFERENCE_MODEL from .env, or defaults to
            'anthropic.claude-sonnet-5').
    Returns:
        A connected BedrockProvider instance ready for .generate(prompt).
    Raises:
        AIConnectionError: same failure modes as get_provider('bedrock').
    """
    resolved_model = model or os.getenv("ANTHROPIC_REFERENCE_MODEL", "anthropic.claude-sonnet-5")
    return get_provider("bedrock", model=resolved_model)


def test_connection(provider: Provider) -> bool:
    """
    Send a trivial prompt and confirm a real response comes back.

    Args:
        provider: a Provider from get_provider().
    Returns:
        True if the round trip succeeded (otherwise raises).
    Raises:
        AIConnectionError: propagated from provider.generate() on failure,
            so a notebook cell fails loudly with a specific message instead
            of silently continuing with a broken connection.
    """
    print(f"Testing connection to '{provider.name}' (model={provider.model})...")
    result = provider.generate("Reply with exactly the word: pong", max_tokens=10)
    print(f"  Response: {result.text.strip()!r}")
    print(f"PASS -- '{provider.name}' is reachable and responding.")
    return True
