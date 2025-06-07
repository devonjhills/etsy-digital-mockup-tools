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

## Improved Extensible Architecture

### Source Structure (`src/`)
- **`src/core/`**: Core framework (base_processor, processor_factory, config_manager)
- **`src/app/`**: Web application (Flask app, routes, templates)
- **`src/products/`**: Product-specific processors organized by type
- **`src/services/`**: Shared business logic and integrations
- **`src/utils/`**: Shared utilities and helper functions

### Product Processors (`src/products/`)
- **`src/products/pattern/`**: Pattern-specific processor and logic
  - `processor.py`: PatternProcessor with `@register_processor("pattern")`
  - `seamless.py`: Seamless pattern creation logic
  - `dynamic_main_mockup.py`: Pattern mockup generation
  - `layered.py`: Layered pattern mockups
- **`src/products/clipart/`**: Clipart-specific processor and logic
  - `processor.py`: ClipartProcessor with `@register_processor("clipart")`
  - `mockups.py`: Clipart mockup generation
  - `transparency.py`: Transparency demonstration
  - `utils.py`: Clipart-specific utilities
- **`src/products/wall_art/`**: Wall art processor (ready for expansion)

### Shared Services (`src/services/`)
- **`src/services/ai/`**: AI provider integration
  - `providers/`: AI provider implementations (Gemini, OpenAI)
- **`src/services/etsy/`**: Etsy marketplace integration
  - Complete Etsy API integration and listing management
- **`src/services/processing/`**: Generic processing engines
  - `grid.py`: Grid creation for all product types
  - `video.py`: Video creation using MoviePy
  - `resize.py`: Image resizing utilities
- **`src/services/file_ops/`**: File operations and validation

### Web Application (`src/app/`)
- **`src/app/main.py`**: Streamlined Flask application
- **`src/app/routes/`**: Route handlers (ready for API/web separation)
- **`src/app/templates/`**: HTML templates

### Shared Utilities (`src/utils/`)
- **`ai_utils.py`**: Unified AI provider management
- **`env_loader.py`**: Environment variable loading with validation
- **`file_operations.py`**: ZIP creation, directory management
- **`video_utils.py`**: Video creation utilities
- **`image_utils.py`**: Image processing utilities
- **`color_utils.py`**: Color analysis and palette generation
- **`text_utils.py`**: Text processing and layout utilities
- **`common.py`**: Common utilities and logging
- **`grid_utils.py`**: Grid layout utilities
- **`resize_utils.py`**: Image resizing utilities

### Entry Points
- **`main.py`**: Unified CLI entry point (imports from `src/`)
- **`src/app/main.py`**: Web interface entry point

## Adding New Product Types

### Method 1: Code-based Registration
```python
# Create src/products/wall_art/processor.py
from src.core.base_processor import BaseProcessor
from src.core.processor_factory import register_processor

@register_processor("wall_art")  # Automatic registration
class WallArtProcessor(BaseProcessor):
    def get_default_workflow_steps(self):
        return ["resize", "mockup", "frame", "zip"]
    
    def resize_images(self):
        # Custom resize logic using src/utils/resize_utils
        pass
    
    def create_mockups(self):
        # Custom mockup logic using src/services/processing
        pass
```

### Method 2: Configuration-driven (YAML)
```yaml
# config/product_types/wall_art.yaml
name: wall_art
display_name: "Wall Art & Prints"
processor_class: "src.products.wall_art.processor.WallArtProcessor"
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
- Edit `src/app/main.py` and `src/app/templates/app.html`
- All processing uses processor classes directly (no CLI calls)
- Real-time logging and status updates

### For Adding Product Types
1. Create processor class in `src/products/new_type/processor.py`
2. Use `@register_processor("type_name")` decorator
3. Import the processor in `main.py` to register it
4. Product type automatically appears in GUI and CLI

### For Modifying Processing Logic
- Edit specific processor class methods
- Changes automatically available in both GUI and CLI
- Shared utilities in `src/utils/` for common operations

### Testing
```bash
# Test specific processor
python main.py process pattern input/test-pattern --steps resize

# Test AI content generation
python main.py generate-content clipart input/test-clipart

# Test full workflow via GUI at http://localhost:8096
```

## Configuration System

Use `src/core/config_manager.py` for all configuration needs:

```python
from src.core.config_manager import get_config_manager

config_manager = get_config_manager()
pattern_config = config_manager.get_config("pattern")
workflow_steps = config_manager.get_workflow_steps("pattern")
ai_prompt = config_manager.get_ai_prompt("pattern", "title")
```

This architecture eliminates code duplication, makes adding new product types trivial, and provides a much cleaner development experience focused on the GUI interface.