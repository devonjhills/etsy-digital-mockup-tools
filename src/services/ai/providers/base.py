"""
Base class for AI providers.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class AIProvider(ABC):
    """Base class for AI providers."""

    def __init__(self, api_key: str, model_name: str):
        """
        Initialize the AI provider.

        Args:
            api_key: API key for the provider
            model_name: Name of the model to use
        """
        self.api_key = api_key
        self.model_name = model_name

    @abstractmethod
    def generate_content_from_image(
        self, image_path: str, instructions: str
    ) -> Dict[str, Any]:
        """
        Generate content (title, description, tags) from an image.

        Args:
            image_path: Path to the image file
            instructions: Instructions for the AI

        Returns:
            Dictionary with title, description, and tags
        """
        pass
