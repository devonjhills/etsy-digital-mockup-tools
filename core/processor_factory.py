"""
Factory for creating product type processors.
Centralizes processor creation and registration.
"""

from typing import Dict, Type, List
from .base_processor import BaseProcessor, ProcessingConfig


class ProcessorRegistry:
    """Registry for product type processors."""
    
    def __init__(self):
        self._processors: Dict[str, Type[BaseProcessor]] = {}
    
    def register(self, product_type: str, processor_class: Type[BaseProcessor]):
        """Register a processor for a product type."""
        self._processors[product_type] = processor_class
    
    def get_processor_class(self, product_type: str) -> Type[BaseProcessor]:
        """Get processor class for a product type."""
        if product_type not in self._processors:
            raise ValueError(f"Unknown product type: {product_type}")
        return self._processors[product_type]
    
    def list_available_types(self) -> List[str]:
        """List all registered product types."""
        return list(self._processors.keys())
    
    def is_registered(self, product_type: str) -> bool:
        """Check if a product type is registered."""
        return product_type in self._processors


class ProcessorFactory:
    """Factory for creating product processors."""
    
    # Global registry instance
    _registry = ProcessorRegistry()
    
    @classmethod
    def register_processor(cls, product_type: str, processor_class: Type[BaseProcessor]):
        """Register a processor class for a product type."""
        cls._registry.register(product_type, processor_class)
    
    @classmethod
    def create_processor(cls, config: ProcessingConfig) -> BaseProcessor:
        """Create a processor instance for the given configuration."""
        processor_class = cls._registry.get_processor_class(config.product_type)
        return processor_class(config)
    
    @classmethod
    def get_available_types(cls) -> List[str]:
        """Get list of available product types."""
        return cls._registry.list_available_types()
    
    @classmethod
    def supports_type(cls, product_type: str) -> bool:
        """Check if a product type is supported."""
        return cls._registry.is_registered(product_type)


def register_processor(product_type: str):
    """Decorator for registering processor classes."""
    def decorator(processor_class: Type[BaseProcessor]):
        ProcessorFactory.register_processor(product_type, processor_class)
        return processor_class
    return decorator