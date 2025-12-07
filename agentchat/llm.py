"""LLM provider configuration and factory."""

import os
from typing import Literal, cast

from langchain_core.language_models.chat_models import BaseChatModel

LLMProvider = Literal["anthropic", "bedrock"]

DEFAULT_MODELS: dict[LLMProvider, str] = {
    "anthropic": "claude-sonnet-4-5-20250929",
    "bedrock": "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
}


def get_provider() -> LLMProvider:
    """Get LLM provider from LLM_PROVIDER env var. Default: anthropic."""
    provider = os.environ.get("LLM_PROVIDER", "anthropic").lower()
    if provider not in ("anthropic", "bedrock"):
        raise ValueError(f"Invalid LLM_PROVIDER: {provider}. Must be 'anthropic' or 'bedrock'.")
    return cast(LLMProvider, provider)


def get_default_model(provider: LLMProvider | None = None) -> str:
    """Get default model for provider. MODEL_ID env var overrides."""
    if provider is None:
        provider = get_provider()
    return os.environ.get("MODEL_ID") or DEFAULT_MODELS[provider]


def create_chat_model(
    model_name: str | None = None,
    provider: LLMProvider | None = None,
) -> BaseChatModel:
    """Create chat model for configured provider.

    Args:
        model_name: Model ID. If None, uses default for provider.
        provider: Provider to use. If None, reads from LLM_PROVIDER env var.

    Returns:
        BaseChatModel instance (ChatAnthropic or ChatBedrockConverse).

    Raises:
        ValueError: If provider is invalid.
    """
    if provider is None:
        provider = get_provider()
    if model_name is None:
        model_name = get_default_model(provider)

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(model=model_name)

    elif provider == "bedrock":
        from langchain_aws import ChatBedrockConverse

        region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")
        return ChatBedrockConverse(model_id=model_name, region_name=region)

    raise ValueError(f"Unknown provider: {provider}")
