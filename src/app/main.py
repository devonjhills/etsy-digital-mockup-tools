#!/usr/bin/env python3
"""
Streamlined web-based GUI for mockup tools.
Uses the new processor architecture for direct function calls.
"""

import os
import sys
import threading
import webbrowser
from pathlib import Path
from flask import Flask, render_template, request, jsonify

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# Import our new architecture
from src.core.processor_factory import ProcessorFactory
from src.core.base_processor import ProcessingConfig
from src.utils.env_loader import setup_environment
from src.utils.ai_utils import get_available_providers
from src.utils.common import ensure_dir_exists

# Import processors to register them
from src.products.pattern.processor import PatternProcessor
from src.products.clipart.processor import ClipartProcessor
from src.products.border_clipart.processor import BorderClipartProcessor
from src.products.journal_papers.processor import JournalPapersProcessor

# Global variables for logging
log_messages = []
processing_status = {"current_task": None, "is_running": False}

# Initialize Flask app
app = Flask(__name__)

# Ensure required directories exist
ensure_dir_exists("input")
ensure_dir_exists("templates")


def add_log(message: str, level: str = "info"):
    """Add a message to the log with color coding."""
    global log_messages

    # Determine message type and add color/emoji coding
    # Check for success conditions first (higher priority)
    if (
        level == "success"
        or "✓" in message
        or "success" in message.lower()
        or "completed" in message.lower()
    ):
        formatted_msg = f"🟢 {message}"
        level = "success"
    elif (
        level == "error"
        or "✗" in message
        or ("failed" in message.lower() and "successful" not in message.lower())
        or "error" in message.lower()
    ):
        formatted_msg = f"🔴 {message}"
        level = "error"
    elif "warning" in message.lower() or "warn" in message.lower():
        formatted_msg = f"� {message}"
        level = "warning"
    else:
        formatted_msg = f"ℹ️ {message}"
        level = "info"

    # Only add to GUI logs, no console output
    log_messages.append(
        {
            "message": formatted_msg,
            "level": level,
            "timestamp": __import__("time").time(),
        }
    )

    # Keep only last 100 messages to prevent memory issues
    if len(log_messages) > 100:
        log_messages = log_messages[-100:]


def run_processor_workflow(
    processor_type: str,
    input_dir: str,
    workflow_steps: list = None,
    custom_settings: dict = None,
) -> dict:
    """Run a processor workflow and return results."""
    try:
        # Validate input directory
        if not os.path.exists(input_dir):
            return {
                "success": False,
                "error": f"Input directory not found: {input_dir}",
            }

        # Use input directory for nested output folders
        output_dir = input_dir

        # Create configuration
        config = ProcessingConfig(
            product_type=processor_type,
            input_dir=input_dir,
            output_dir=output_dir,
            custom_settings=custom_settings or {},
        )

        # Create processor
        processor = ProcessorFactory.create_processor(config)

        # Run workflow
        add_log(f"Starting {processor_type} workflow for {input_dir}")
        results = processor.run_workflow(workflow_steps)

        add_log(f"Completed {processor_type} workflow successfully")
        return {"success": True, "results": results, "output_dir": output_dir}

    except Exception as e:
        error_msg = f"Workflow failed: {str(e)}"
        add_log(error_msg)
        return {"success": False, "error": error_msg}


# Routes
@app.route("/")
def index():
    """Main page."""
    return render_template("app.html")


@app.route("/log")
def get_log():
    """Get recent log messages."""
    global log_messages
    messages = log_messages.copy()
    log_messages.clear()  # Clear after reading
    return jsonify({"messages": messages})


@app.route("/status")
def get_status():
    """Get current processing status."""
    return jsonify(processing_status)


@app.route("/get-subfolders")
def get_subfolders():
    """Get all subfolders in the input directory."""
    try:
        input_dir = "input"
        ensure_dir_exists(input_dir)

        subfolders = [
            f
            for f in os.listdir(input_dir)
            if os.path.isdir(os.path.join(input_dir, f)) and not f.startswith(".")
        ]

        return jsonify({"subfolders": sorted(subfolders)})
    except Exception as e:
        return jsonify({"error": str(e), "subfolders": []})


@app.route("/get-available-types")
def get_available_types():
    """Get available processor types."""
    try:
        types = ProcessorFactory.get_available_types()
        return jsonify({"types": types})
    except Exception as e:
        return jsonify({"error": str(e), "types": []})


@app.route("/get-ai-providers")
def get_ai_providers():
    """Get available AI providers."""
    try:
        providers = get_available_providers()
        return jsonify({"providers": providers})
    except Exception as e:
        return jsonify({"error": str(e), "providers": {}})


def run_all_subfolders_workflow(
    processor_type: str, workflow_steps: list = None, custom_settings: dict = None
) -> dict:
    """Run a processor workflow on all subfolders in the input directory."""
    try:
        input_base_dir = "input"

        # Get all subfolders
        if not os.path.exists(input_base_dir):
            return {
                "success": False,
                "error": f"Input directory not found: {input_base_dir}",
            }

        subfolders = [
            f
            for f in os.listdir(input_base_dir)
            if os.path.isdir(os.path.join(input_base_dir, f)) and not f.startswith(".")
        ]

        if not subfolders:
            return {"success": False, "error": "No subfolders found in input directory"}

        add_log(f"Found {len(subfolders)} folders to process: {', '.join(subfolders)}")

        all_results = {}
        successful_count = 0
        failed_count = 0

        for subfolder in subfolders:
            input_dir = os.path.join(input_base_dir, subfolder)
            output_dir = input_dir  # Use input directory for nested output folders

            add_log(f"Processing folder: {subfolder}")

            # Create configuration for this subfolder
            config = ProcessingConfig(
                product_type=processor_type,
                input_dir=input_dir,
                output_dir=output_dir,
                custom_settings=custom_settings or {},
            )

            try:
                # Create processor
                processor = ProcessorFactory.create_processor(config)

                # Run workflow (detailed logging handled by processor)
                result = processor.run_workflow(workflow_steps)
                all_results[subfolder] = result

                if result.get("success", True):
                    successful_count += 1
                    add_log(f"✓ Completed {subfolder} - output saved to {output_dir}")
                else:
                    failed_count += 1
                    add_log(
                        f"✗ Failed {subfolder}: {result.get('error', 'Unknown error')}"
                    )

            except Exception as e:
                failed_count += 1
                error_msg = f"Error processing {subfolder}: {str(e)}"
                add_log(f"✗ {error_msg}")
                all_results[subfolder] = {"success": False, "error": str(e)}

        # Summary
        total = len(subfolders)
        add_log(
            f"Batch processing complete: {successful_count}/{total} successful, {failed_count}/{total} failed"
        )

        return {
            "success": failed_count == 0,
            "total_folders": total,
            "successful": successful_count,
            "failed": failed_count,
            "results": all_results,
        }

    except Exception as e:
        error_msg = f"Batch workflow failed: {str(e)}"
        add_log(error_msg)
        return {"success": False, "error": error_msg}


@app.route("/run-workflow", methods=["POST"])
def run_workflow():
    """Run a processing workflow on all subfolders in input directory."""
    try:
        data = request.json
        add_log(f"Received workflow request: {data}")

        # Extract parameters
        processor_type = data.get("processor_type")
        workflow_steps = data.get("workflow_steps")
        custom_settings = data.get("custom_settings", {})

        # Validate required parameters
        if not processor_type:
            add_log("Error: processor_type is required", "error")
            return jsonify({"error": "processor_type is required"}), 400

        # Check if processor type is supported
        if not ProcessorFactory.supports_type(processor_type):
            add_log(f"Error: Unsupported processor type: {processor_type}", "error")
            return (
                jsonify({"error": f"Unsupported processor type: {processor_type}"}),
                400,
            )

        add_log(f"Starting {processor_type} workflow with steps: {workflow_steps}")

        # Set processing status
        processing_status["current_task"] = f"{processor_type} batch workflow"
        processing_status["is_running"] = True

        def run_in_background():
            try:
                result = run_all_subfolders_workflow(
                    processor_type=processor_type,
                    workflow_steps=workflow_steps,
                    custom_settings=custom_settings,
                )

                # Update status
                processing_status["current_task"] = None
                processing_status["is_running"] = False
                processing_status["last_result"] = result

            except Exception as e:
                add_log(f"Background task failed: {e}", "error")
                processing_status["current_task"] = None
                processing_status["is_running"] = False
                processing_status["last_result"] = {"success": False, "error": str(e)}

        # Start background thread
        thread = threading.Thread(target=run_in_background)
        thread.start()

        add_log(f"Successfully started {processor_type} batch workflow", "success")

        return jsonify(
            {
                "message": "Batch workflow started",
                "processor_type": processor_type,
                "workflow_steps": workflow_steps,
                "mode": "all_subfolders",
            }
        )

    except Exception as e:
        add_log(f"Workflow startup failed: {str(e)}", "error")
        processing_status["current_task"] = None
        processing_status["is_running"] = False
        return jsonify({"error": str(e)}), 500


@app.route("/generate-etsy-content", methods=["POST"])
def generate_etsy_content():
    """Generate Etsy listing content using AI."""
    try:
        data = request.json
        processor_type = data.get("processor_type", "pattern")
        input_dir = data.get("input_dir")
        ai_provider = data.get("ai_provider", "gemini")

        if not input_dir:
            return jsonify({"error": "input_dir is required"}), 400

        # Create configuration
        config = ProcessingConfig(
            product_type=processor_type,
            input_dir=input_dir,
            output_dir=input_dir,  # Use input directory for nested folders
            ai_provider=ai_provider,
        )

        # Create processor and generate content
        processor = ProcessorFactory.create_processor(config)
        content = processor.generate_etsy_content()

        return jsonify(
            {"success": True, "content": content, "processor_type": processor_type}
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/prepare-etsy-listings", methods=["POST"])
def prepare_etsy_listings():
    """Prepare Etsy listings with AI-generated content from mockup images."""
    try:
        data = request.json
        processor_type = data.get("processor_type", "pattern")
        ai_provider = data.get("ai_provider", "gemini")

        add_log(f"Starting Etsy listing preparation for {processor_type} products")

        # Import Etsy integration
        from src.services.etsy.main import EtsyIntegration
        from src.services.etsy.constants import DEFAULT_ETSY_INSTRUCTIONS
        from src.utils.env_loader import get_env_var

        # Get AI API key
        if ai_provider == "gemini":
            ai_api_key = get_env_var("GEMINI_API_KEY")
        else:
            ai_api_key = get_env_var("OPENAI_API_KEY")

        if not ai_api_key:
            return (
                jsonify(
                    {
                        "error": f"{ai_provider.upper()} API key not configured. Please set it in your .env file."
                    }
                ),
                400,
            )

        # Initialize Etsy integration with AI provider
        etsy = EtsyIntegration(
            etsy_api_key="dummy",  # Not needed for preparation
            etsy_api_secret="dummy",  # Not needed for preparation
            api_key=ai_api_key,
            provider_type=ai_provider,
        )

        # Set processing status
        processing_status["current_task"] = (
            f"Preparing {processor_type} listings with AI"
        )
        processing_status["is_running"] = True

        def run_listing_preparation():
            try:
                # Prepare listings for all subfolders in input directory
                input_base_dir = "input"
                prepared_listings = etsy.prepare_bulk_listings(
                    input_dir=input_base_dir,
                    product_type=processor_type,
                    skip_mockups=True,  # Assume mockups already exist
                    skip_zips=True,  # Assume zips already exist
                    skip_resize=True,  # Assume images already resized
                )

                # Save prepared listings to file
                import json

                output_file = "prepared_listings.json"
                with open(output_file, "w") as f:
                    json.dump(prepared_listings, f, indent=2)

                # Update status
                processing_status["current_task"] = None
                processing_status["is_running"] = False
                processing_status["last_result"] = {
                    "success": True,
                    "listings_prepared": len(prepared_listings),
                    "output_file": output_file,
                    "listings": prepared_listings,
                }

                add_log(f"Successfully prepared {len(prepared_listings)} Etsy listings")
                add_log(f"Listings saved to {output_file}")

            except Exception as e:
                add_log(f"Listing preparation failed: {str(e)}")
                processing_status["current_task"] = None
                processing_status["is_running"] = False
                processing_status["last_result"] = {"success": False, "error": str(e)}

        # Start background thread
        import threading

        thread = threading.Thread(target=run_listing_preparation)
        thread.start()

        return jsonify(
            {
                "message": f"Started preparing {processor_type} listings with AI",
                "ai_provider": ai_provider,
            }
        )

    except Exception as e:
        processing_status["current_task"] = None
        processing_status["is_running"] = False
        return jsonify({"error": str(e)}), 500


@app.route("/full-bulk-processing", methods=["POST"])
def full_bulk_processing():
    """Run complete bulk processing workflow: resize, mockups, zips, then AI content generation."""
    try:
        data = request.json
        processor_type = data.get("processor_type", "pattern")
        ai_provider = data.get("ai_provider", "gemini")

        add_log(f"Starting full bulk processing for {processor_type} products")

        # Import Etsy integration
        from src.services.etsy.main import EtsyIntegration
        from src.services.etsy.constants import DEFAULT_ETSY_INSTRUCTIONS
        from src.utils.env_loader import get_env_var

        # Get AI API key
        if ai_provider == "gemini":
            ai_api_key = get_env_var("GEMINI_API_KEY")
        else:
            ai_api_key = get_env_var("OPENAI_API_KEY")

        if not ai_api_key:
            return (
                jsonify(
                    {
                        "error": f"{ai_provider.upper()} API key not configured. Please set it in your .env file."
                    }
                ),
                400,
            )

        # Initialize Etsy integration with AI provider
        etsy = EtsyIntegration(
            etsy_api_key="dummy",  # Not needed for preparation
            etsy_api_secret="dummy",  # Not needed for preparation
            api_key=ai_api_key,
            provider_type=ai_provider,
        )

        # Set processing status
        processing_status["current_task"] = f"Full processing {processor_type} products"
        processing_status["is_running"] = True

        def run_full_processing():
            try:
                # Run complete bulk processing (resize, mockups, zips, then AI content)
                input_base_dir = "input"
                prepared_listings = etsy.prepare_bulk_listings(
                    input_dir=input_base_dir,
                    product_type=processor_type,
                    skip_mockups=False,  # Create mockups
                    skip_zips=False,  # Create zips
                    skip_resize=False,  # Resize images
                )

                # Save prepared listings to file
                import json

                output_file = "prepared_listings.json"
                with open(output_file, "w") as f:
                    json.dump(prepared_listings, f, indent=2)

                # Update status
                processing_status["current_task"] = None
                processing_status["is_running"] = False
                processing_status["last_result"] = {
                    "success": True,
                    "listings_prepared": len(prepared_listings),
                    "output_file": output_file,
                    "listings": prepared_listings,
                    "workflow": "full_processing",
                }

                add_log(
                    f"Successfully completed full processing and prepared {len(prepared_listings)} Etsy listings"
                )
                add_log(f"Listings saved to {output_file}")

            except Exception as e:
                add_log(f"Full bulk processing failed: {str(e)}")
                processing_status["current_task"] = None
                processing_status["is_running"] = False
                processing_status["last_result"] = {"success": False, "error": str(e)}

        # Start background thread
        import threading

        thread = threading.Thread(target=run_full_processing)
        thread.start()

        return jsonify(
            {
                "message": f"Started full bulk processing for {processor_type} products",
                "ai_provider": ai_provider,
                "workflow": "full_processing",
            }
        )

    except Exception as e:
        processing_status["current_task"] = None
        processing_status["is_running"] = False
        return jsonify({"error": str(e)}), 500


@app.route("/get-prepared-listings")
def get_prepared_listings():
    """Get prepared listings if they exist."""
    try:
        import json
        import os

        prepared_file = "prepared_listings.json"
        if os.path.exists(prepared_file):
            with open(prepared_file, "r") as f:
                prepared_listings = json.load(f)

            return jsonify(
                {
                    "success": True,
                    "listings": prepared_listings,
                    "count": len(prepared_listings),
                }
            )
        else:
            return jsonify(
                {
                    "success": False,
                    "listings": [],
                    "count": 0,
                    "message": "No prepared listings found",
                }
            )

    except Exception as e:
        return jsonify({"success": False, "error": str(e), "listings": [], "count": 0})


@app.route("/update-prepared-listing", methods=["POST"])
def update_prepared_listing():
    """Update a specific prepared listing."""
    try:
        import json
        import os

        data = request.json
        folder_name = data.get("folder_name")
        title = data.get("title", "").strip()
        description = data.get("description", "").strip()
        tags = data.get("tags", [])

        # Validation
        if not folder_name:
            return jsonify({"error": "folder_name is required"}), 400

        # Title validation (140 characters max)
        if len(title) > 140:
            return (
                jsonify(
                    {
                        "error": f"Title must be 140 characters or less (currently {len(title)} characters)"
                    }
                ),
                400,
            )

        # Tags validation (20 characters each, max 13 tags)
        if len(tags) > 13:
            return (
                jsonify(
                    {"error": f"Maximum 13 tags allowed (currently {len(tags)} tags)"}
                ),
                400,
            )

        for i, tag in enumerate(tags):
            tag = tag.strip()
            if len(tag) > 20:
                return (
                    jsonify(
                        {
                            "error": f"Tag '{tag}' is {len(tag)} characters. Each tag must be 20 characters or less."
                        }
                    ),
                    400,
                )
            tags[i] = tag  # Update with trimmed version

        # Load existing prepared listings
        prepared_file = "prepared_listings.json"
        if not os.path.exists(prepared_file):
            return jsonify({"error": "No prepared listings found"}), 400

        with open(prepared_file, "r") as f:
            prepared_listings = json.load(f)

        # Find and update the specific listing
        listing_found = False
        for listing in prepared_listings:
            if listing.get("folder_name") == folder_name:
                listing["title"] = title
                listing["description"] = description
                listing["tags"] = tags
                listing_found = True
                break

        if not listing_found:
            return (
                jsonify({"error": f"Listing for folder '{folder_name}' not found"}),
                404,
            )

        # Save updated listings
        with open(prepared_file, "w") as f:
            json.dump(prepared_listings, f, indent=2)

        add_log(f"Updated listing for {folder_name}")

        return jsonify(
            {
                "success": True,
                "message": f"Successfully updated listing for {folder_name}",
                "updated_listing": {
                    "folder_name": folder_name,
                    "title": title,
                    "description": description,
                    "tags": tags,
                },
            }
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/delete-prepared-listings", methods=["POST"])
def delete_prepared_listings():
    """Delete prepared listings file."""
    try:
        import os

        prepared_file = "prepared_listings.json"

        if os.path.exists(prepared_file):
            # Create backup before deletion
            backup_file = "prepared_listings_backup.json"
            if os.path.exists(backup_file):
                os.remove(backup_file)
            os.rename(prepared_file, backup_file)

            add_log("Prepared listings deleted successfully (backup saved)")

            return jsonify(
                {
                    "success": True,
                    "message": "Prepared listings deleted successfully",
                    "backup_created": True,
                }
            )
        else:
            return jsonify(
                {"success": False, "message": "No prepared listings found to delete"}
            )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/delete-single-prepared-listing", methods=["POST"])
def delete_single_prepared_listing():
    """Delete a single prepared listing."""
    try:
        import json
        import os

        data = request.json
        folder_name = data.get("folder_name")

        if not folder_name:
            return jsonify({"error": "folder_name is required"}), 400

        # Load existing prepared listings
        prepared_file = "prepared_listings.json"
        if not os.path.exists(prepared_file):
            return jsonify({"error": "No prepared listings found"}), 400

        with open(prepared_file, "r") as f:
            prepared_listings = json.load(f)

        # Find and remove the specific listing
        initial_count = len(prepared_listings)
        prepared_listings = [
            listing
            for listing in prepared_listings
            if listing.get("folder_name") != folder_name
        ]

        if len(prepared_listings) == initial_count:
            return (
                jsonify({"error": f"Listing for folder '{folder_name}' not found"}),
                404,
            )

        # Save updated listings
        with open(prepared_file, "w") as f:
            json.dump(prepared_listings, f, indent=2)

        add_log(f"Deleted prepared listing for {folder_name}")

        return jsonify(
            {
                "success": True,
                "message": f"Successfully deleted prepared listing for {folder_name}",
                "remaining_count": len(prepared_listings),
            }
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/upload-prepared-listings", methods=["POST"])
def upload_prepared_listings():
    """Upload previously prepared listings to Etsy."""
    try:
        data = request.json
        is_draft = data.get("is_draft", True)

        add_log("Starting upload of prepared listings to Etsy")

        # Import Etsy integration
        from src.services.etsy.main import EtsyIntegration
        from src.utils.env_loader import get_env_var
        import json
        import os

        # Check if prepared listings exist
        prepared_file = "prepared_listings.json"
        if not os.path.exists(prepared_file):
            return (
                jsonify(
                    {
                        "error": "No prepared listings found. Please prepare listings first."
                    }
                ),
                400,
            )

        # Load prepared listings
        with open(prepared_file, "r") as f:
            prepared_listings = json.load(f)

        if not prepared_listings:
            return jsonify({"error": "No listings found in prepared file."}), 400

        # Get Etsy credentials
        etsy_api_key = get_env_var("ETSY_API_KEY")
        etsy_api_secret = get_env_var("ETSY_API_SECRET")

        if not etsy_api_key or not etsy_api_secret:
            return (
                jsonify(
                    {
                        "error": "Etsy API credentials not configured. Please set ETSY_API_KEY and ETSY_API_SECRET in your .env file."
                    }
                ),
                400,
            )

        # Initialize Etsy integration
        etsy = EtsyIntegration(
            etsy_api_key=etsy_api_key, etsy_api_secret=etsy_api_secret
        )

        # Authenticate with Etsy
        if not etsy.authenticate():
            return (
                jsonify(
                    {
                        "error": "Failed to authenticate with Etsy. Please check your credentials."
                    }
                ),
                400,
            )

        # Set processing status
        processing_status["current_task"] = (
            f"Uploading {len(prepared_listings)} listings to Etsy"
        )
        processing_status["is_running"] = True

        def run_etsy_upload():
            try:
                uploaded_listings = []
                failed_listings = []
                successfully_uploaded_folders = []

                for listing_data in prepared_listings:
                    try:
                        add_log(f"Uploading listing: {listing_data['folder_name']}")
                        result = etsy.upload_prepared_listing(
                            listing_data, is_draft=is_draft
                        )

                        if result:
                            uploaded_listings.append(result)
                            successfully_uploaded_folders.append(
                                listing_data["folder_name"]
                            )
                            listing_id = result.get("listing_id")
                            add_log(
                                f"✓ Successfully uploaded: {listing_data['folder_name']} (ID: {listing_id})"
                            )
                        else:
                            failed_listings.append(listing_data["folder_name"])
                            add_log(
                                f"✗ Failed to upload: {listing_data['folder_name']}"
                            )

                    except Exception as e:
                        failed_listings.append(listing_data["folder_name"])
                        add_log(
                            f"✗ Error uploading {listing_data['folder_name']}: {str(e)}"
                        )

                # Remove successfully uploaded listings from prepared_listings.json
                if successfully_uploaded_folders:
                    try:
                        # Filter out successfully uploaded listings
                        remaining_listings = [
                            listing
                            for listing in prepared_listings
                            if listing["folder_name"]
                            not in successfully_uploaded_folders
                        ]

                        # Update the prepared listings file
                        with open(prepared_file, "w") as f:
                            json.dump(remaining_listings, f, indent=2)

                        if remaining_listings:
                            add_log(
                                f"✓ Removed {len(successfully_uploaded_folders)} uploaded listings from prepared list. {len(remaining_listings)} listings remaining."
                            )
                        else:
                            add_log(
                                f"✓ All prepared listings uploaded successfully. Prepared listings cleared."
                            )

                    except Exception as e:
                        add_log(
                            f"Warning: Could not update prepared listings file: {str(e)}",
                            "warning",
                        )

                # Update status
                processing_status["current_task"] = None
                processing_status["is_running"] = False
                processing_status["last_result"] = {
                    "success": len(failed_listings) == 0,
                    "uploaded_count": len(uploaded_listings),
                    "failed_count": len(failed_listings),
                    "uploaded_listings": uploaded_listings,
                    "failed_listings": failed_listings,
                    "removed_from_prepared": successfully_uploaded_folders,
                }

                add_log(
                    f"Upload complete: {len(uploaded_listings)} successful, {len(failed_listings)} failed"
                )

            except Exception as e:
                add_log(f"Etsy upload failed: {str(e)}")
                processing_status["current_task"] = None
                processing_status["is_running"] = False
                processing_status["last_result"] = {"success": False, "error": str(e)}

        # Start background thread
        import threading

        thread = threading.Thread(target=run_etsy_upload)
        thread.start()

        return jsonify(
            {
                "message": f"Started uploading {len(prepared_listings)} prepared listings to Etsy",
                "is_draft": is_draft,
                "listings_count": len(prepared_listings),
            }
        )

    except Exception as e:
        processing_status["current_task"] = None
        processing_status["is_running"] = False
        return jsonify({"error": str(e)}), 500


def main():
    """Main function to start the application."""
    # Setup GUI logging integration
    from src.utils.common import set_gui_log_function

    set_gui_log_function(add_log)

    # Setup environment
    if not setup_environment():
        add_log("Environment setup failed. Please check your .env file.", "error")
        return

    # Check available processors
    available_types = ProcessorFactory.get_available_types()
    add_log(f"Available processors: {', '.join(available_types)}")

    # Check available AI providers
    providers = get_available_providers()
    available_ai = [name for name, available in providers.items() if available]
    if available_ai:
        add_log(f"Available AI providers: {', '.join(available_ai)}")
    else:
        add_log(
            "Warning: No AI providers configured. AI features will be disabled.",
            "warning",
        )

    # Start Flask app
    port = 8096
    add_log(f"Web interface ready at http://localhost:{port}", "success")

    # Open browser
    def open_browser():
        webbrowser.open(f"http://localhost:{port}")

    threading.Timer(1.0, open_browser).start()

    # Run Flask app (suppress console output)
    try:
        import logging

        log = logging.getLogger("werkzeug")
        log.setLevel(logging.ERROR)  # Only show errors from Flask

        app.run(debug=False, host="0.0.0.0", port=port, use_reloader=False)
    except KeyboardInterrupt:
        add_log("Application stopped by user", "info")
    except Exception as e:
        add_log(f"Application error: {e}", "error")


if __name__ == "__main__":
    main()
