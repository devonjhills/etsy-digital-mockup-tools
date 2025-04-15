# Mockup Tools: Digital Product Automation Suite

<div align="center">

_A comprehensive toolkit for digital product creators and Etsy sellers_

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.0%2B-green)](https://flask.palletsprojects.com/)
[![Etsy API](https://img.shields.io/badge/Etsy%20API-v3-orange)](https://developer.etsy.com/)
[![Google Gemini](https://img.shields.io/badge/Google%20Gemini-AI-purple)](https://ai.google.dev/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

</div>

## 🚀 Overview

Mockup Tools is a powerful automation suite designed for digital product creators, Etsy sellers, and e-commerce entrepreneurs. This project showcases advanced Python development skills, API integration expertise, and AI implementation capabilities.

The toolkit streamlines the entire workflow from product creation to Etsy listing, automating repetitive tasks and leveraging AI to generate SEO-optimized content.

## ✨ Key Features

### 🎨 Product Processing

- **Pattern Processing**: Resize, rename, and prepare seamless pattern files
- **Clipart Processing**: Optimize clipart images for digital downloads
- **Batch Processing**: Handle multiple products in a single operation

### 🖼️ Mockup Generation

- **Dynamic Mockups**: Create professional product mockups with color extraction
- **Grid Layouts**: Generate multi-image grid displays
- **Video Creation**: Produce promotional videos for listings

### 🔄 Etsy Integration

- **OAuth Authentication**: Secure API authentication with PKCE
- **Listing Creation**: Automated listing creation with all required fields
- **Digital File Upload**: Streamlined upload of digital products
- **Bulk Operations**: Create multiple listings in a single batch

### 🤖 AI-Powered Content

- **SEO Optimization**: Generate listing titles, descriptions, and tags
- **Image Analysis**: Extract product details from mockup images
- **Content Generation**: Create compelling marketing copy
- **AI-Powered**: Leverages Google Gemini 2.0 Flash for intelligent content generation

### 🖥️ User Interface

- **Web-Based GUI**: Easy-to-use interface built with Flask
- **Real-Time Logs**: Monitor operations with live updates
- **Responsive Design**: Works on desktop and mobile devices

## 🛠️ Technical Implementation

### Architecture

The project follows a modular architecture with clear separation of concerns:

```
mockup-tools/
├── pattern/         # Pattern processing modules
├── clipart/         # Clipart processing modules
├── etsy/            # Etsy API integration
├── utils/           # Shared utilities
├── templates/       # Web UI templates
├── assets/          # Static assets
├── cli.py           # Command-line interface
└── gui.py           # Web-based interface
```

### Technologies

- **Python**: Core language for all processing logic
- **Flask**: Web framework for the GUI
- **Pillow (PIL)**: Image processing and manipulation
- **OpenCV**: Advanced image processing and video creation
- **AI Integration**: Google Gemini 2.0 Flash for image analysis and content generation
- **Etsy API v3**: E-commerce platform integration
- **OAuth 2.0**: Secure authentication with PKCE flow
- **JavaScript/CSS**: Frontend enhancements

## 📊 Demonstrated Skills

### Software Engineering

- **Object-Oriented Design**: Clean, modular architecture
- **API Integration**: RESTful API consumption and OAuth implementation
- **Error Handling**: Robust error management and logging
- **Testing**: Comprehensive test coverage

### Python Development

- **Modern Python**: Type hints, f-strings, context managers
- **Package Management**: Proper dependency handling
- **Asynchronous Operations**: Efficient processing of multiple tasks
- **CLI Development**: Intuitive command-line interfaces

### Web Development

- **Flask Application**: Lightweight web server implementation
- **Responsive Design**: Mobile-friendly interface
- **AJAX**: Asynchronous updates without page reloads
- **Frontend Skills**: JavaScript, HTML5, and CSS3

### AI Integration

- **Prompt Engineering**: Crafting effective AI prompts for Gemini 2.0 Flash
- **Content Generation**: AI-powered SEO optimization
- **Image Analysis**: Extracting meaningful content from product images

### Image Processing

- **Algorithmic Image Manipulation**: Advanced transformations
- **Color Analysis**: Extraction and palette generation
- **Video Creation**: Programmatic video production

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

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   ```bash
   cp .env.local .env
   # Edit .env with your API keys
   ```

### Configuration

Create a `.env` file with the following variables:

```
# Etsy API credentials
ETSY_API_KEY="your_etsy_api_key_here"
ETSY_API_SECRET="your_etsy_api_secret_here"
ETSY_SHOP_ID="your_etsy_shop_id_here"

# Google Gemini API credentials
GEMINI_API_KEY="your_gemini_api_key_here"
GEMINI_MODEL="gemini-2.0-flash"
```

### API Setup

1. **Etsy API**:

   - Register as a developer at https://www.etsy.com/developers/register
   - Create a new app to get your API key and secret
   - Set the OAuth redirect URI to `http://localhost:3003/oauth/redirect`

2. **Google Gemini API**:

   - Visit https://ai.google.dev/ to get an API key
   - Enable the Gemini API for your project

### Running the Application

#### Web Interface

```bash
python gui.py
```

This will start the web server and automatically open the interface in your browser.

#### Command Line

```bash
# Process patterns
python cli.py pattern all --input_dir input/patterns

# Create Etsy listings
python cli.py etsy bulk-create --input_dir input/patterns --product_type pattern
```

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
