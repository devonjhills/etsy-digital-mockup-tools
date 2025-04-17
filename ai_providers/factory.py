"""
Factory for creating AI providers.
"""

import os
import logging
from typing import Optional, Dict, Any

from .base import AIProvider
from .gemini_provider import GeminiProvider
from .openai_provider import OpenAIProvider

# Set up logging
from utils.common import setup_logging

logger = setup_logging(__name__)


class AIProviderFactory:
    """Factory for creating AI providers."""

    @staticmethod
    def create_provider(
        provider_type: str, api_key: str = None, model_name: str = None
    ) -> Optional[AIProvider]:
        """
        Create an AI provider.

        Args:
            provider_type: Type of provider to create ('gemini', 'openai')
            api_key: API key for the provider (if None, will try to get from environment)
            model_name: Name of the model to use (if None, will try to get from environment)

        Returns:
            An AI provider or None if creation failed
        """
        provider_type = provider_type.lower()

        if provider_type == "gemini":
            # Get API key from environment if not provided
            if not api_key:
                api_key = os.environ.get("GEMINI_API_KEY")
                if not api_key:
                    logger.error("GEMINI_API_KEY not found in environment variables")
                    return None

            # Get model name from environment if not provided
            if not model_name:
                model_name = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

            return GeminiProvider(api_key, model_name)

        elif provider_type == "openai":
            # Get API key from environment if not provided
            if not api_key:
                api_key = os.environ.get("OPENAI_API_KEY")
                if not api_key:
                    logger.error("OPENAI_API_KEY not found in environment variables")
                    return None

            # Get model name from environment if not provided
            if not model_name:
                model_name = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")

            return OpenAIProvider(api_key, model_name)

        else:
            logger.error(f"Unknown provider type: {provider_type}")
            return None

    @staticmethod
    def get_default_provider() -> Optional[AIProvider]:
        """
        Get the default AI provider based on environment variables.

        First tries to use the provider specified in AI_PROVIDER environment variable.
        If not set, falls back to OpenAI if OPENAI_API_KEY is available,
        then to Gemini if GEMINI_API_KEY is available.

        Returns:
            An AI provider or None if creation failed
        """
        # Check if AI_PROVIDER is explicitly set
        provider_type = os.environ.get("AI_PROVIDER")
        if provider_type:
            logger.info(f"Using {provider_type} as provider (from AI_PROVIDER env var)")
            return AIProviderFactory.create_provider(provider_type)

        # If not set, prioritize OpenAI
        if os.environ.get("OPENAI_API_KEY"):
            logger.info("Using OpenAI as default provider")
            return AIProviderFactory.create_provider("openai")

        # Fall back to Gemini
        if os.environ.get("GEMINI_API_KEY"):
            logger.info("Using Gemini as default provider")
            return AIProviderFactory.create_provider("gemini")

        logger.error("No API keys found in environment variables")
        return None
