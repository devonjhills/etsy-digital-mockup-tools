# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Mockup Tools** is a streamlined automation suite for digital product creators and Etsy sellers. The codebase has been refactored to use a unified processor architecture with GUI-first design, eliminating CLI duplication and making it easy to add new product types.

## Running the Application

### Primary Interface (GUI)
```bash
# Start the streamlined web interface (recommended)
python main.py
# or
python main.py gui

# Runs on http://localhost:8096 with real-time processing and logging
```

### Optional Command Line Interface
```bash
# Process products directly (uses same processor architecture as GUI)
python main.py process pattern input/my-pattern
python main.py process clipart input/my-clipart

# Generate AI content only
python main.py generate-content pattern input/my-pattern --ai-provider gemini

# List available product types
python main.py list-types
```

### Installation & Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Environment setup
cp .env.local .env
# Edit .env with API keys for Etsy and AI providers
```

## Streamlined Architecture

### Core Framework (`core/`)
- **`base_processor.py`**: Abstract base class for all product processors
- **`processor_factory.py`**: Factory pattern with automatic registration system
- **`config_manager.py`**: Unified configuration system for all product types

### Processors (`processors/`)
- **`pattern_processor.py`**: Seamless pattern processing using `@register_processor("pattern")`
- **`clipart_processor.py`**: Clipart/illustration processing using `@register_processor("clipart")`
- **Easy Extension**: New processors automatically register and appear in GUI

### Consolidated Utilities (`utils/`)
- **`ai_utils.py`**: Unified AI provider management (Gemini/OpenAI)
- **`env_loader.py`**: Environment variable loading with validation
- **`file_operations.py`**: ZIP creation, directory management, file operations
- **`video_utils.py`**: Video creation using MoviePy
- **`image_utils.py`**: Shared image processing utilities
- **`color_utils.py`**: Color analysis and palette generation
- **`text_utils.py`**: Text processing and layout utilities

### Single Entry Point
- **`main.py`**: Unified entry point replacing all CLI modules
- **`app.py`**: Streamlined Flask GUI using processor architecture directly (no subprocess calls)

## Adding New Product Types

### Method 1: Code-based Registration
```python
# Create new processor class
from core.base_processor import BaseProcessor
from core.processor_factory import register_processor

@register_processor("wall_art")  # Automatic registration
class WallArtProcessor(BaseProcessor):
    def get_default_workflow_steps(self):
        return ["resize", "mockup", "frame", "zip"]
    
    def resize_images(self):
        # Custom resize logic
        pass
    
    def create_mockups(self):
        # Custom mockup logic  
        pass
```

### Method 2: Configuration-driven (YAML)
```yaml
# config/product_types/wall_art.yaml
name: wall_art
display_name: "Wall Art & Prints"
processor_class: "processors.wall_art_processor.WallArtProcessor"
default_workflow_steps: ["resize", "mockup", "frame", "zip"]
resize_settings:
  max_size: 4000
  format: "jpg"
  quality: 95
mockup_settings:
  create_framed: true
  frame_styles: ["modern", "classic", "rustic"]
ai_prompts:
  title: "Create an Etsy title for this wall art print..."
  description: "Write a description for this wall art..."
```

### Automatic GUI Integration
New product types automatically appear in the GUI dropdown - no GUI code changes needed.

## Key Architectural Improvements

### Eliminated Duplication
- **No more CLI subprocess calls**: GUI uses processor classes directly
- **Unified AI management**: Single `get_ai_provider()` function
- **Consolidated utilities**: Shared image, file, and video operations
- **Single configuration system**: Replace scattered config files

### Extensibility
- **Factory pattern**: New processors self-register
- **Configuration-driven**: Add product types via YAML without code changes
- **Workflow customization**: Easy to modify or extend processing steps
- **Plugin architecture**: Processors are completely independent

### Simplified Data Flow
1. **GUI/CLI** → **ProcessorFactory** → **Specific Processor**
2. **Processor** → **Shared Utilities** → **Direct Function Calls**
3. **No subprocess overhead** or **CLI parameter marshaling**

## Environment Variables

Same as before, but now loaded through unified `utils/env_loader.py`:

```bash
# Required
ETSY_API_KEY="your_etsy_api_key_here"
ETSY_API_SECRET="your_etsy_api_secret_here"  
ETSY_SHOP_ID="your_etsy_shop_id_here"

# Optional (at least one AI provider recommended)
GEMINI_API_KEY="your_gemini_api_key_here"
OPENAI_API_KEY="your_openai_api_key_here"
```

## Development Workflow

### For GUI Development
- Edit `app.py` and `templates/app.html`
- All processing uses processor classes directly (no CLI calls)
- Real-time logging and status updates

### For Adding Product Types
1. Create processor class in `processors/`
2. Use `@register_processor("type_name")` decorator
3. Product type automatically appears in GUI and CLI

### For Modifying Processing Logic
- Edit specific processor class methods
- Changes automatically available in both GUI and CLI
- Shared utilities in `utils/` for common operations

### Testing
```bash
# Test specific processor
python main.py process pattern input/test-pattern --steps resize

# Test AI content generation
python main.py generate-content clipart input/test-clipart

# Test full workflow via GUI at http://localhost:8096
```

## Configuration System

Use `core/config_manager.py` for all configuration needs:

```python
from core.config_manager import get_config_manager

config_manager = get_config_manager()
pattern_config = config_manager.get_config("pattern")
workflow_steps = config_manager.get_workflow_steps("pattern")
ai_prompt = config_manager.get_ai_prompt("pattern", "title")
```

This architecture eliminates code duplication, makes adding new product types trivial, and provides a much cleaner development experience focused on the GUI interface.