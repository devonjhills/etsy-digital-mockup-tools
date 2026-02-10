#!/usr/bin/env python3
"""
Main entry point for Mockup Tools.
Provides both GUI and optional command-line interface using the unified processor architecture.
"""

import os
import sys
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.core.processor_factory import ProcessorFactory
from src.core.base_processor import ProcessingConfig
from src.core.config_manager import get_config_manager
from src.utils.env_loader import setup_environment
from src.utils.common import setup_logging

# Import processors to register them
from src.products.pattern.processor import PatternProcessor
from src.products.clipart.processor import ClipartProcessor
from src.products.border_clipart.processor import BorderClipartProcessor
from src.products.journal_papers.processor import JournalPapersProcessor

logger = setup_logging(__name__, gui_only=False)  # CLI should use console logging


def create_parser():
    """Create argument parser for command-line interface."""
    parser = argparse.ArgumentParser(
        description="Mockup Tools - Digital Product Processing Suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s gui                                    # Start web interface (default)
  %(prog)s process pattern input/my-pattern       # Process pattern with default workflow
  %(prog)s process clipart input/my-clipart       # Process clipart with default workflow
  %(prog)s process pattern input/my-pattern --steps resize mockup  # Custom workflow steps
  %(prog)s list-types                             # List available product types
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # GUI command (default)
    gui_parser = subparsers.add_parser('gui', help='Start web interface')
    gui_parser.add_argument('--port', type=int, default=8096, help='Port to run web interface on')
    
    # Process command
    process_parser = subparsers.add_parser('process', help='Process digital products')
    process_parser.add_argument('product_type', help='Type of product to process')
    process_parser.add_argument('input_dir', help='Input directory containing images')
    process_parser.add_argument('--output-dir', help='Output directory (default: {product_type}_output)')
    process_parser.add_argument('--steps', nargs='*', help='Workflow steps to run')
    process_parser.add_argument('--ai-provider', default='gemini', choices=['gemini', 'openai'], 
                               help='AI provider for content generation')
    process_parser.add_argument('--no-video', action='store_true', help='Skip video creation')
    process_parser.add_argument('--no-zip', action='store_true', help='Skip ZIP file creation')
    
    # List types command
    list_parser = subparsers.add_parser('list-types', help='List available product types')
    
    # Generate content command
    content_parser = subparsers.add_parser('generate-content', help='Generate AI content for Etsy listings')
    content_parser.add_argument('product_type', help='Type of product')
    content_parser.add_argument('input_dir', help='Input directory containing images')
    content_parser.add_argument('--ai-provider', default='gemini', choices=['gemini', 'openai'])
    
    
    return parser


def run_gui(args):
    """Start the web interface."""
    try:
        from src.app.main import main as app_main
        app_main()
    except ImportError as e:
        logger.error(f"Failed to import GUI module: {e}")
        sys.exit(1)


def run_process(args):
    """Process digital products using the processor framework."""
    try:
        # Validate product type
        if not ProcessorFactory.supports_type(args.product_type):
            available_types = ProcessorFactory.get_available_types()
            logger.error(f"Unknown product type: {args.product_type}")
            logger.error(f"Available types: {', '.join(available_types)}")
            sys.exit(1)
        
        # Validate input directory
        if not os.path.exists(args.input_dir):
            logger.error(f"Input directory not found: {args.input_dir}")
            sys.exit(1)
        
        # Determine output directory
        output_dir = args.output_dir
        if not output_dir:
            input_name = Path(args.input_dir).name
            output_dir = f"{args.product_type}_output/{input_name}"
        
        # Get workflow steps
        config_manager = get_config_manager()
        workflow_steps = config_manager.get_workflow_steps(args.product_type, args.steps)
        
        # Remove video/zip steps if disabled
        if args.no_video and 'video' in workflow_steps:
            workflow_steps.remove('video')
        if args.no_zip and 'zip' in workflow_steps:
            workflow_steps.remove('zip')
        
        # Create configuration
        config = ProcessingConfig(
            product_type=args.product_type,
            input_dir=args.input_dir,
            output_dir=output_dir,
            ai_provider=args.ai_provider,
            create_video=not args.no_video,
            create_zip=not args.no_zip
        )
        
        # Create and run processor
        logger.info(f"Processing {args.product_type} from {args.input_dir}")
        logger.info(f"Workflow steps: {', '.join(workflow_steps)}")
        
        processor = ProcessorFactory.create_processor(config)
        results = processor.run_workflow(workflow_steps)
        
        logger.info("Processing completed successfully!")
        logger.info(f"Output saved to: {output_dir}")
        
        # Print summary
        print("\n" + "="*60)
        print("PROCESSING SUMMARY")
        print("="*60)
        print(f"Product Type: {args.product_type}")
        print(f"Input Directory: {args.input_dir}")
        print(f"Output Directory: {output_dir}")
        print(f"Workflow Steps: {', '.join(workflow_steps)}")
        print(f"Status: {'SUCCESS' if all(r.get('success', True) for r in results.values() if isinstance(r, dict)) else 'PARTIAL'}")
        print("="*60)
        
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        sys.exit(1)


def run_list_types(args):
    """List available product types."""
    config_manager = get_config_manager()
    types = config_manager.list_product_types()
    
    print("\nAvailable Product Types:")
    print("-" * 40)
    
    for product_type in types:
        config = config_manager.get_config(product_type)
        if config:
            print(f"  {product_type:<12} - {config.display_name}")
            print(f"               Steps: {', '.join(config.default_workflow_steps)}")
        else:
            print(f"  {product_type}")
    
    print()


def run_generate_content(args):
    """Generate AI content for Etsy listings."""
    try:
        # Validate inputs
        if not ProcessorFactory.supports_type(args.product_type):
            logger.error(f"Unknown product type: {args.product_type}")
            sys.exit(1)
        
        if not os.path.exists(args.input_dir):
            logger.error(f"Input directory not found: {args.input_dir}")
            sys.exit(1)
        
        # Create configuration
        config = ProcessingConfig(
            product_type=args.product_type,
            input_dir=args.input_dir,
            output_dir="temp_output",
            ai_provider=args.ai_provider
        )
        
        # Generate content
        logger.info(f"Generating AI content for {args.product_type} using {args.ai_provider}")
        
        processor = ProcessorFactory.create_processor(config)
        content = processor.generate_etsy_content()
        
        if content and not content.get('error'):
            print("\n" + "="*60)
            print("GENERATED ETSY CONTENT")
            print("="*60)
            
            if 'title' in content:
                print(f"\nTitle:\n{content['title']}")
            
            if 'description' in content:
                print(f"\nDescription:\n{content['description']}")
            
            if 'tags' in content and content['tags']:
                print(f"\nTags:\n{', '.join(content['tags'])}")
            
            print("\n" + "="*60)
        else:
            error = content.get('error', 'Unknown error') if content else 'No content generated'
            logger.error(f"Content generation failed: {error}")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Content generation failed: {e}")
        sys.exit(1)




def main():
    """Main entry point."""
    # Setup environment first
    if not setup_environment():
        print("Environment setup failed. Please check your .env file.")
        return
    
    # Parse arguments
    parser = create_parser()
    args = parser.parse_args()
    
    # Default to GUI if no command specified
    if not args.command:
        args.command = 'gui'
        args.port = 8096
    
    # Route to appropriate handler
    if args.command == 'gui':
        run_gui(args)
    elif args.command == 'process':
        run_process(args)
    elif args.command == 'list-types':
        run_list_types(args)
    elif args.command == 'generate-content':
        run_generate_content(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()