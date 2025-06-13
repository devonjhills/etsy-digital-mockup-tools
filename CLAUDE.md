# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Mockup Tools** is a comprehensive automation suite for digital product creators and Etsy sellers. The application features a unified processor architecture with a modern web GUI that handles full bulk processing workflows including image processing, mockup generation, and AI-powered Etsy listing creation.

## Running the Application

### Primary Interface (GUI)
```bash
# Start the streamlined web interface (recommended)
python main.py
# or
python main.py gui

# Runs on http://localhost:8096 with real-time processing and logging
```

### Command Line Interface
```bash
# Process products directly (uses same processor architecture as GUI)
python main.py process pattern input/my-pattern
python main.py process clipart input/my-clipart

# Generate AI content only
python main.py generate-content pattern input/my-pattern --ai-provider gemini

# List available product types
python main.py list-types
```

### Quick Setup Scripts
```bash
# macOS/Linux setup and run
./activate.sh    # Sets up virtual environment and dependencies
./run.sh         # Starts the GUI

# Windows setup and run
activate.bat     # Sets up virtual environment and dependencies
run.bat          # Starts the GUI
```

### Installation & Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Environment setup
cp .env.local .env
# Edit .env with API keys for Etsy and AI providers
```

## Modern Architecture

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
- **`src/products/border_clipart/`**: Border clipart processor
  - `processor.py`: BorderClipartProcessor with specialized seamless border processing
  - `mockups.py`: Border-specific mockup generation
- **`src/products/journal_papers/`**: Journal papers processor
  - `processor.py`: JournalPapersProcessor for printable journal pages
- **`src/products/wall_art/`**: Wall art processor (ready for expansion)

### Shared Services (`src/services/`)
- **`src/services/ai/`**: AI provider integration
  - `providers/`: AI provider implementations (Gemini, OpenAI)
- **`src/services/etsy/`**: Complete Etsy marketplace integration
  - `auth.py`: OAuth authentication with PKCE
  - `listings.py`: Listing creation and management
  - `content.py`: AI-powered content generation
  - `main.py`: Main EtsyIntegration class for bulk operations
  - `templates.py`: Listing template management
  - `constants.py`: Etsy-specific constants and configurations
- **`src/services/processing/`**: Generic processing engines
  - `video.py`: Video creation using MoviePy
  - `mockups/`: Mockup generation base classes
- **`src/services/file_ops/`**: File operations and validation

### Web Application (`src/app/`)
- **`src/app/main.py`**: Modern Flask application with comprehensive routes
- **`src/app/routes/`**: Route handlers (ready for expansion)
- **`src/app/templates/`**: Modern web UI with Catppuccin theme

### Shared Utilities (`src/utils/`)
- **`ai_utils.py`**: Unified AI provider management
- **`env_loader.py`**: Environment variable loading with validation
- **`file_operations.py`**: ZIP creation, directory management
- **`video_utils.py`**: Video creation utilities
- **`image_utils.py`**: Image processing utilities
- **`color_utils.py`**: Color analysis and palette generation
- **`text_utils.py`**: Text processing and layout utilities
- **`common.py`**: Common utilities and logging with GUI integration
- **`grid_utils.py`**: Grid layout utilities
- **`resize_utils.py`**: Image resizing utilities
- **`mockup_utils.py`**: Mockup generation utilities

### Entry Points
- **`main.py`**: Unified CLI entry point with comprehensive command support
- **`src/app/main.py`**: Web interface entry point

### Configuration & Templates
- **`templates/`**: JSON templates for Etsy listings by product type
- **`assets/`**: Static assets including fonts, logos, mockup overlays

## Web Interface Features

### Core Workflows
The web GUI provides comprehensive automation workflows:

1. **Bulk Processing Workflow**: Process all subfolders in `input/` directory
   - Resize images to optimal dimensions
   - Generate professional mockups (main, grid, layered, transparency demos)
   - Create promotional videos
   - Package files into ZIP archives

2. **Full Bulk Processing**: Complete end-to-end workflow
   - All image processing steps
   - AI-powered Etsy listing content generation
   - Prepared listings ready for upload

3. **Etsy Listing Preparation**: AI-powered content generation
   - Analyze product images using AI
   - Generate SEO-optimized titles, descriptions, and tags
   - Create listings based on product-specific templates
   - Save prepared listings for review and editing

4. **Etsy Upload**: Direct upload to Etsy marketplace
   - Upload prepared listings to Etsy
   - Support for draft and active listings
   - Automatic removal of uploaded listings from prepared queue

### Real-time Features
- **Live logging**: Real-time processing updates with emoji indicators
- **Status monitoring**: Current task tracking and progress indication
- **Background processing**: Non-blocking operations with threading
- **Responsive design**: Modern Catppuccin-themed interface

### Product Type Support
The application supports multiple product types with specialized processing:

- **Pattern**: Seamless patterns with dynamic color extraction
- **Clipart**: Transparent PNG cliparts with grid layouts
- **Border Clipart**: Seamless horizontal border elements
- **Journal Papers**: Printable journal pages (8.5x11)

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

### Method 2: Configuration-driven
Configurations are managed in `src/core/config_manager.py` with built-in support for:
- Resize settings (dimensions, format, DPI)
- Mockup settings (layouts, styles, output sizes)
- Font and typography settings
- Color and layout configurations
- AI prompts for content generation
- Etsy listing templates

### Automatic Integration
New product types automatically:
- Appear in the GUI dropdown
- Work with bulk processing workflows
- Support AI content generation
- Integrate with Etsy upload system

## Key Features & Architecture

### Core Capabilities
- **Unified Processing**: GUI and CLI use the same processor architecture
- **Bulk Operations**: Process multiple product folders simultaneously
- **AI Integration**: Gemini and OpenAI providers for content generation
- **Etsy Integration**: Complete OAuth workflow and listing management
- **Real-time UI**: Live logging and status updates with modern design

### Architecture Benefits
- **Factory pattern**: Processors self-register using decorators
- **Configuration-driven**: Centralized config management in `config_manager.py`
- **Modular design**: Independent processors with shared utilities
- **Direct function calls**: No subprocess overhead between GUI and processing logic

### Data Flow
1. **Web GUI** → **Flask Routes** → **ProcessorFactory** → **Specific Processor**
2. **Processor** → **Shared Services & Utilities** → **Direct Function Calls**
3. **Real-time logging** via GUI integration hooks

## Environment Variables

Configuration is loaded through `src/utils/env_loader.py`:

```bash
# Required for Etsy integration
ETSY_API_KEY="your_etsy_api_key_here"
ETSY_API_SECRET="your_etsy_api_secret_here"  
ETSY_SHOP_ID="your_etsy_shop_id_here"

# AI providers (at least one recommended for content generation)
GEMINI_API_KEY="your_gemini_api_key_here"
OPENAI_API_KEY="your_openai_api_key_here"
```

## Development Workflow

### GUI Development
- Main Flask app: `src/app/main.py`
- UI template: `src/app/templates/app.html` (Catppuccin-themed)
- All processing uses processor classes directly
- Real-time logging with emoji indicators and status tracking

### Adding Product Types
1. Create processor class in `src/products/new_type/processor.py`
2. Use `@register_processor("type_name")` decorator
3. Import the processor in `main.py` to register it
4. Add configuration in `src/core/config_manager.py`
5. Create Etsy template in `templates/new_type.json`
6. Product type automatically appears in GUI and CLI

### Modifying Processing Logic
- Edit specific processor class methods
- Changes automatically available in both GUI and CLI
- Shared utilities in `src/utils/` for common operations
- Configuration changes in `config_manager.py`

### Testing Workflows
```bash
# Test specific processor via CLI
python main.py process pattern input/test-pattern

# Test AI content generation
python main.py generate-content clipart input/test-clipart

# Test full workflow via web GUI
python main.py gui  # Visit http://localhost:8096
```

### Etsy Integration Testing
1. Use "Prepare Etsy Listings" to generate AI content
2. Review and edit prepared listings in the GUI
3. Use "Upload to Etsy" to create draft listings
4. Test OAuth flow and listing management

## Configuration System

Centralized configuration management via `src/core/config_manager.py`:

```python
from src.core.config_manager import get_config_manager

config_manager = get_config_manager()
pattern_config = config_manager.get_config("pattern")
workflow_steps = config_manager.get_workflow_steps("pattern")
ai_prompt = config_manager.get_ai_prompt("pattern", "title")
mockup_settings = config_manager.get_mockup_settings("pattern")
```

The architecture provides a comprehensive automation suite with modern web interface, AI integration, and full Etsy marketplace support.