# Mockup Tools: Digital Product Automation Suite

<div align="center">

_A comprehensive toolkit for digital product creators and Etsy sellers_

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.0%2B-green)](https://flask.palletsprojects.com/)
[![Etsy API](https://img.shields.io/badge/Etsy%20API-v3-orange)](https://developer.etsy.com/)
[![Google Gemini](https://img.shields.io/badge/Google%20Gemini-AI-purple)](https://ai.google.dev/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

<img width="1252" height="603" alt="Screenshot 2025-07-31 at 4 51 39 PM" src="https://github.com/user-attachments/assets/8c2284db-622a-456c-ad2b-4b349eccee26" />


</div>

## 🚀 Overview

Mockup Tools is a powerful automation suite designed for digital product creators, Etsy sellers, and e-commerce entrepreneurs. This project showcases advanced Python development skills, API integration expertise, and AI implementation capabilities.

The toolkit streamlines the entire workflow from product creation to Etsy listing, automating repetitive tasks and leveraging AI to generate SEO-optimized content.

## ✨ Key Features

### 🎨 Advanced Product Processing

- **Multi-Product Support**: Seamless patterns, clipart, border clipart, and journal papers
- **Intelligent Resizing**: Optimized dimensions and quality for each product type
- **Batch Processing**: Process multiple product folders simultaneously
- **Professional Mockups**: Dynamic color extraction, grid layouts, transparency demos

### 🖼️ Comprehensive Mockup Generation

- **Dynamic Main Mockups**: Color-extracted titles and professional layouts
- **Grid Compositions**: Multi-image displays with configurable layouts
- **Specialized Mockups**: Seamless borders, transparency demonstrations, layered previews
- **Video Creation**: Promotional videos for social media and listings

### 🔄 Complete Etsy Integration

- **OAuth 2.0 + PKCE**: Secure authentication flow
- **Bulk Listing Creation**: Process entire product catalogs
- **Template System**: Product-specific listing templates
- **Draft & Active Support**: Upload as drafts or active listings
- **Automatic Management**: Remove uploaded listings from preparation queue

### 🤖 AI-Powered Content Generation

- **Multi-Provider Support**: Google Gemini and OpenAI integration
- **Image Analysis**: Intelligent product detail extraction
- **SEO Optimization**: Generate compelling titles, descriptions, and tags
- **Contextual Content**: Product-specific prompts and templates
- **Editable Results**: Review and modify AI-generated content before upload

### 🖥️ Modern Web Interface

- **Catppuccin Theme**: Beautiful, modern dark interface
- **Real-Time Logging**: Live updates with emoji indicators and color coding
- **Background Processing**: Non-blocking operations with progress tracking
- **Responsive Design**: Works seamlessly on all devices
- **Status Monitoring**: Current task tracking and completion status

## 🛠️ Technical Implementation

### Architecture

The project follows a modern, modular architecture with unified processing:

```
mockup-tools/
├── src/
│   ├── core/               # Core framework (processors, config)
│   ├── app/                # Flask web application
│   ├── products/           # Product-specific processors
│   │   ├── pattern/        # Seamless pattern processing
│   │   ├── clipart/        # Clipart processing
│   │   ├── border_clipart/ # Border clipart processing  
│   │   └── journal_papers/ # Journal pages processing
│   ├── services/           # Shared business logic
│   │   ├── ai/             # AI provider integration
│   │   ├── etsy/           # Complete Etsy integration
│   │   └── processing/     # Generic processing engines
│   └── utils/              # Shared utilities
├── templates/              # Etsy listing templates (JSON)
├── assets/                 # Static assets (fonts, logos)
├── input/                  # Product input folders
└── main.py                 # Unified entry point
```

### Technologies

- **Python 3.8+**: Modern Python with type hints and async capabilities
- **Flask**: Lightweight web framework with real-time features
- **Pillow (PIL)**: Advanced image processing and manipulation
- **MoviePy**: Video creation and editing
- **AI Integration**: Google Gemini and OpenAI for content generation
- **Etsy API v3**: Complete marketplace integration with OAuth 2.0 + PKCE
- **Modern Frontend**: HTML5, CSS3 (Catppuccin theme), JavaScript
- **Background Processing**: Threading for non-blocking operations

## 📊 Demonstrated Skills

### Software Engineering

- **Modern Architecture**: Factory pattern, dependency injection, decorator-based registration
- **API Integration**: RESTful APIs, OAuth 2.0 + PKCE, error handling and retry logic
- **Real-time Systems**: Background processing, live logging, status tracking
- **Configuration Management**: Centralized, type-safe configuration system

### Python Development

- **Advanced Python**: Type hints, dataclasses, context managers, decorators
- **Async Processing**: Threading, background tasks, non-blocking operations  
- **Package Architecture**: Clean imports, modular design, shared utilities
- **CLI & Web**: Unified codebase serving both interfaces

### Web Development

- **Modern Flask**: Real-time updates, background processing, RESTful APIs
- **Frontend Excellence**: Responsive design, modern CSS (Catppuccin), dynamic UI
- **User Experience**: Live logging, progress indicators, intuitive workflows
- **State Management**: Session handling, real-time status updates

### AI & Machine Learning

- **Multi-Provider Integration**: Gemini and OpenAI with unified interface
- **Prompt Engineering**: Context-aware, product-specific prompts
- **Image Analysis**: AI-powered content extraction and SEO optimization
- **Content Generation**: Automated title, description, and tag creation

### Image & Video Processing

- **Advanced Manipulation**: Dynamic color extraction, transparency handling
- **Mockup Generation**: Professional layouts with typography and branding
- **Video Production**: Automated promotional video creation
- **Batch Processing**: Efficient handling of multiple product catalogs

### E-commerce Integration

- **Marketplace APIs**: Complete Etsy integration with listing management
- **Automation Workflows**: End-to-end product-to-listing pipelines
- **Template Systems**: Product-specific listing configurations
- **Bulk Operations**: Scalable processing of entire product catalogs

## 📸 Screenshots

<div align="center">

_Screenshots will be added as the project develops_

```
+----------------------------------+
|                                  |
|          Web Interface           |
|                                  |
|  +----------------------------+  |
|  |                            |  |
|  |       Pattern Tools        |  |
|  |                            |  |
|  +----------------------------+  |
|                                  |
|  +----------------------------+  |
|  |                            |  |
|  |       Etsy Integration     |  |
|  |                            |  |
|  +----------------------------+  |
|                                  |
+----------------------------------+
```

</div>

## 🚀 Getting Started

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Google Gemini API key

### Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/mockup-tools.git
   cd mockup-tools
   ```

2. **Quick Setup** (Automatic virtual environment and dependencies):

   **macOS/Linux:**
   ```bash
   ./activate.sh
   ```

   **Windows:**
   ```bash
   activate.bat
   ```

   **Manual Setup** (if you prefer):
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   ```bash
   cp .env.local .env
   # Edit .env with your API keys
   ```

### Configuration

Create a `.env` file with the following variables:

```bash
# Etsy API credentials (required for marketplace integration)
ETSY_API_KEY="your_etsy_api_key_here"
ETSY_API_SECRET="your_etsy_api_secret_here"
ETSY_SHOP_ID="your_etsy_shop_id_here"

# AI providers (at least one recommended)
GEMINI_API_KEY="your_gemini_api_key_here"
OPENAI_API_KEY="your_openai_api_key_here"
```

### API Setup

1. **Etsy API**:

   - Register as a developer at https://www.etsy.com/developers/register
   - Create a new app to get your API key and secret
   - Set the OAuth redirect URI to `http://localhost:3003/oauth/redirect`

2. **AI Providers**:

   - **Google Gemini**: Visit https://ai.google.dev/ to get an API key
   - **OpenAI**: Visit https://platform.openai.com/ for API access

### Running the Application

#### Quick Launch (Recommended)

**macOS/Linux:**
```bash
./run.sh                    # Start GUI
./run.sh list-types         # List available product types
./run.sh --help            # Show all options
```

**Windows:**
```bash
run.bat                     # Start GUI
run.bat list-types          # List available product types
run.bat --help             # Show all options
```

#### Manual Launch (after activating virtual environment)

**Web Interface (Recommended):**
```bash
python main.py                  # Start GUI (default)
python main.py gui              # Explicit GUI start
```
The web interface runs on http://localhost:8096 with:
- Real-time processing logs with emoji indicators
- Background processing with progress tracking  
- Modern Catppuccin-themed interface
- Complete workflow management

**Command Line Options:**
```bash
# Process products directly
python main.py process pattern input/my-pattern
python main.py process border_clipart input/my-borders

# Generate AI content only  
python main.py generate-content clipart input/my-clipart --ai-provider gemini

# List available product types
python main.py list-types
```

### Supported Product Types

- **pattern**: Seamless patterns with dynamic color extraction
- **clipart**: Transparent PNG cliparts with grid layouts
- **border_clipart**: Seamless horizontal border elements
- **journal_papers**: Printable journal pages (8.5x11)

### Complete Workflows

1. **Bulk Processing**: Process all folders in `input/` directory
2. **AI Content Generation**: Create Etsy-ready titles, descriptions, tags
3. **Etsy Integration**: Upload listings directly to your Etsy shop
4. **Review & Edit**: Modify AI-generated content before upload

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Contact & Portfolio

For more examples of my work and professional inquiries:

- **GitHub**: [github.com/devonjhills](https://github.com/devonjhills)
- **LinkedIn**: [linkedin.com/in/devonjhills](https://linkedin.com/in/devonjhills)
- **Email**: devonjhills@gmail.com

---

<div align="center">

_This project demonstrates expertise in Python development, API integration, image processing, and AI implementation._

</div>
