"""
OpenRouter AI provider implementation.
"""

import os
import base64
import re
import io
import logging
import time
import json
import requests
from typing import Optional, Dict, Any, List, Tuple
from PIL import Image

from .base import AIProvider

# Set up logging
from utils.common import setup_logging
from utils.ai_utils import process_ai_response, extract_thinking_model_response

logger = setup_logging(__name__)

# Try to import the OpenAI client for OpenRouter compatibility
try:
    from openai import OpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    logger.warning("OpenAI package not found. Install with: pip install openai")
    OPENAI_AVAILABLE = False


class OpenRouterProvider(AIProvider):
    """OpenRouter AI provider implementation."""

    def __init__(self, api_key: str, model_name: str = None):
        """
        Initialize the OpenRouter provider.

        Args:
            api_key: API key for the OpenRouter API
            model_name: Name of the OpenRouter model to use (if None, will use OPEN_ROUTER_MODEL from env)
        """
        # If model_name is not provided, get it from environment variable
        if not model_name:
            model_name = os.environ.get(
                "OPEN_ROUTER_MODEL", "moonshotai/kimi-vl-a3b-thinking:free"
            )

        super().__init__(api_key, model_name)
        self.base_url = "https://openrouter.ai/api/v1"
        self.client = None
        self.timeout = 30  # Increased timeout for thinking models

        # We'll only use the specified model without fallbacks

        # Set up OpenAI client for OpenRouter
        if OPENAI_AVAILABLE:
            self.client = OpenAI(
                base_url=self.base_url,
                api_key=api_key,
                timeout=self.timeout,
            )
            logger.info(f"Initialized OpenRouter with model: {model_name}")
        else:
            logger.error(
                "OpenAI package not available. Install with: pip install openai"
            )

    def _encode_image_to_base64(self, image_path: str) -> Optional[str]:
        """
        Encode an image to base64.

        Args:
            image_path: Path to the image file

        Returns:
            Base64-encoded image or None if encoding failed
        """
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode("utf-8")
        except Exception as e:
            logger.error(f"Error encoding image to base64: {e}")
            return None

    def generate_title_from_image(
        self, image_path: str, max_retries: int = 2
    ) -> Optional[str]:
        """
        Generate a title from an image using OpenRouter API.

        Args:
            image_path: Path to the image file
            max_retries: Maximum number of retries on failure

        Returns:
            A title or None if generation failed
        """
        if not OPENAI_AVAILABLE:
            logger.error(
                "OpenAI package not available. Install with: pip install openai"
            )
            return None

        if not self.client:
            logger.error("OpenRouter client not initialized")
            return None

        if not os.path.exists(image_path):
            logger.error(f"Image file not found: {image_path}")
            return None

        # Get the image file size
        file_size_mb = os.path.getsize(image_path) / (1024 * 1024)
        logger.info(f"Image file size: {file_size_mb:.2f} MB")

        # We'll resize the image to reduce API errors
        img = None

        try:
            # Load the image
            img = Image.open(image_path)
            logger.info(
                f"Image dimensions: {img.width}x{img.height}, format: {img.format}"
            )

            # Always resize the image to reduce API call time and improve reliability
            # Always resize for folder renaming to ensure fast API calls
            logger.info(f"Resizing image for API call")
            # Calculate new dimensions while maintaining aspect ratio
            max_dimension = 512  # Maximum dimension in pixels
            if img.width > img.height:
                new_width = min(img.width, max_dimension)
                new_height = int(img.height * (new_width / img.width))
            else:
                new_height = min(img.height, max_dimension)
                new_width = int(img.width * (new_height / img.height))

            # Resize the image
            img = img.resize((new_width, new_height), Image.LANCZOS)
            logger.info(f"Resized image to {new_width}x{new_height} for API call")

            # Save the resized image to a temporary file
            temp_path = (
                f"{image_path}_temp.{img.format.lower() if img.format else 'png'}"
            )
            img.save(temp_path)
            image_path = temp_path
        except Exception as e:
            logger.error(f"Error loading or resizing image {image_path}: {e}")
            return None

        # Encode the image to base64
        base64_image = self._encode_image_to_base64(image_path)
        if not base64_image:
            return None

        # Try multiple times with increasing timeouts
        for attempt in range(max_retries + 1):
            try:
                # Create the prompt
                prompt = "Look at this image and give me EXACTLY ONE title consisting of 2-3 descriptive words that would make a good folder name based on the visual elements (colors, shapes, style) you see. DO NOT write sentences, explanations, or include words like 'pattern', 'clipart', 'digital', 'design', etc. DO NOT provide multiple options or alternatives. JUST GIVE ME ONE SINGLE TITLE OF 2-3 WORDS IN TITLE CASE, NOTHING ELSE. For example, if you see a red floral pattern, just respond with 'Red Floral' or 'Crimson Flowers' - not both."

                # Create the system message to ensure consistent behavior
                system_message = "You are a folder naming assistant that provides EXACTLY ONE title consisting of 2-3 descriptive words in Title Case based on the visual elements in images. You never provide multiple options, alternatives, or explanations. You respond with a single, concise title and nothing else."

                # Create the messages
                messages = [
                    {"role": "system", "content": system_message},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/{img.format.lower() if img.format else 'png'};base64,{base64_image}"
                                },
                            },
                        ],
                    },
                ]

                # Log attempt information
                logger.info(
                    f"Attempt {attempt + 1}/{max_retries + 1} to generate title with OpenRouter"
                )

                # Generate content
                start_time = time.time()
                try:
                    # Add a format instruction message to force a direct response
                    format_messages = messages.copy()
                    format_messages.append(
                        {
                            "role": "user",
                            "content": "Remember, respond with EXACTLY ONE title of 2-3 words in Title Case. No explanations, no multiple options, no alternatives. Just ONE single title.",
                        }
                    )

                    # For the kimi-vl-a3b-thinking model, we need to increase max_tokens to ensure
                    # we get the full thinking process plus the answer
                    max_tokens_value = (
                        500 if "kimi-vl-a3b-thinking" in self.model_name else 20
                    )

                    response = self.client.chat.completions.create(
                        model=self.model_name,
                        messages=format_messages,
                        max_tokens=max_tokens_value,  # Adjust based on model
                        temperature=0.3,  # Low temperature for more consistent results
                        top_p=0.5,  # Moderate sampling for better output
                        timeout=(
                            60
                            if "kimi-vl-a3b-thinking" in self.model_name
                            else self.timeout
                        ),  # Longer timeout for thinking models
                        response_format={"type": "text"},  # Force text response
                    )
                    elapsed_time = time.time() - start_time
                    logger.info(f"API call completed in {elapsed_time:.2f} seconds")
                except Exception as e:
                    elapsed_time = time.time() - start_time
                    logger.error(
                        f"API call failed after {elapsed_time:.2f} seconds: {e}"
                    )

                    # If we've been waiting too long or on the last retry, log the error
                    if elapsed_time > 5 or attempt == max_retries:
                        logger.error(
                            f"API call failed after multiple attempts with model {self.model_name}"
                        )

                        # If this was the last retry, raise the error
                        if attempt == max_retries:
                            raise
                    elif attempt < max_retries:
                        # Wait before retrying with exponential backoff
                        wait_time = 2 * (attempt + 1)
                        logger.info(
                            f"Waiting {wait_time} seconds before retry {attempt + 2}..."
                        )
                        time.sleep(wait_time)
                    else:
                        raise

                # Get the title from the response
                if not response.choices or not response.choices[0].message.content:
                    logger.error("No content in OpenRouter response")

                    # If we've exhausted all retries and still have no content, return None
                    if attempt == max_retries:
                        logger.error(
                            "Exhausted all retries and still got empty response"
                        )
                        return None
                    elif attempt < max_retries:
                        logger.info(f"Retrying... ({attempt + 1}/{max_retries})")
                        continue
                    else:
                        return None

                # Get the raw response content
                raw_response = response.choices[0].message.content.strip()

                # Log the raw response for debugging
                logger.info(f"DEBUG - Raw model response: {raw_response}")

                # Process the response using our centralized utility function
                # Check if this is a thinking model based on the model name
                is_thinking_model = "thinking" in self.model_name.lower()
                title = process_ai_response(raw_response, is_thinking_model)

                logger.info(f"DEBUG - Processed title: {title}")

                # If title is empty after all the cleaning, use a fallback approach
                if not title:
                    logger.warning(
                        "Title is empty after cleaning, trying a direct approach"
                    )
                    logger.info("DEBUG - Title is empty, using fallback approach")
                    # Try a direct approach with a different model
                    try:
                        # Use a simple, reliable model with a very direct prompt
                        # Try Claude first, then Gemini if available, then other free models
                        fallback_models = [
                            "anthropic/claude-3-haiku:free",  # Claude is reliable for following instructions
                            "google/gemini-1.5-flash:free",  # Gemini is also good
                            "deepseek/deepseek-r1:free",  # DeepSeek is a good fallback
                            "mistralai/mistral-7b-instruct:free",  # Mistral as last resort
                        ]

                        # Try each model until one works
                        for fallback_model in fallback_models:
                            try:
                                logger.info(
                                    f"DEBUG - Trying fallback model: {fallback_model}"
                                )
                                direct_response = self.client.chat.completions.create(
                                    model=fallback_model,
                                    messages=[
                                        {
                                            "role": "system",
                                            "content": "You are a naming assistant that only responds with 2-3 words in Title Case.",
                                        },
                                        {
                                            "role": "user",
                                            "content": "Name this image in 2-3 words based on its visual appearance. ONLY respond with the 2-3 words, nothing else. This is extremely important.",
                                        },
                                    ],
                                    max_tokens=10,
                                    temperature=0.1,
                                )

                                if (
                                    direct_response.choices
                                    and direct_response.choices[0].message.content
                                ):
                                    logger.info(
                                        f"DEBUG - Fallback model {fallback_model} succeeded"
                                    )
                                    break
                            except Exception as e:
                                logger.warning(
                                    f"DEBUG - Fallback model {fallback_model} failed: {e}"
                                )
                                continue

                        if (
                            direct_response.choices
                            and direct_response.choices[0].message.content
                        ):
                            title = direct_response.choices[0].message.content.strip()
                            logger.info(f"Got title from fallback approach: {title}")
                    except Exception as e:
                        logger.error(f"Fallback title generation failed: {e}")

                    # If still empty, use a generic title based on colors in the image
                    if not title:
                        logger.warning(
                            "Fallback title generation failed, using generic title"
                        )
                        # Try to extract colors from the image
                        try:
                            # PIL.Image should already be imported at the top of the file
                            import colorsys

                            # Load the image
                            img = Image.open(image_path)
                            # Resize for faster processing
                            img = img.resize((100, 100))
                            # Convert to RGB
                            img = img.convert("RGB")
                            # Get pixel data
                            pixels = list(img.getdata())

                            # Find dominant colors
                            color_counts = {}
                            for pixel in pixels:
                                if pixel in color_counts:
                                    color_counts[pixel] += 1
                                else:
                                    color_counts[pixel] = 1

                            # Get top 2 colors
                            top_colors = sorted(
                                color_counts.items(), key=lambda x: x[1], reverse=True
                            )[:2]

                            # Convert RGB to HSV to get color names
                            color_names = []
                            for color, _ in top_colors:
                                r, g, b = color
                                h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)

                                # Simple color naming based on HSV
                                if s < 0.1:
                                    if v < 0.3:
                                        color_names.append("Dark")
                                    elif v > 0.7:
                                        color_names.append("Light")
                                    else:
                                        color_names.append("Gray")
                                else:
                                    if h < 0.05 or h > 0.95:
                                        color_names.append("Red")
                                    elif 0.05 <= h < 0.15:
                                        color_names.append("Orange")
                                    elif 0.15 <= h < 0.25:
                                        color_names.append("Yellow")
                                    elif 0.25 <= h < 0.45:
                                        color_names.append("Green")
                                    elif 0.45 <= h < 0.65:
                                        color_names.append("Blue")
                                    elif 0.65 <= h < 0.85:
                                        color_names.append("Purple")
                                    else:
                                        color_names.append("Pink")

                            # Create a title from the color names
                            if (
                                len(color_names) >= 2
                                and color_names[0] != color_names[1]
                            ):
                                title = f"{color_names[0]} {color_names[1]}"
                            elif len(color_names) > 0:
                                title = f"{color_names[0]} Design"
                            else:
                                title = "Colorful Design"

                            logger.info(f"Generated color-based title: {title}")
                        except Exception as e:
                            logger.error(f"Color extraction failed: {e}")
                            title = "Elegant Design"  # Last resort fallback

                # Enforce maximum of 3 words
                words = title.split()
                if len(words) > 3:
                    logger.warning(
                        f"Title has {len(words)} words, truncating to 3 words"
                    )
                    title = " ".join(words[:3])

                # Remove any product type terms that might have slipped through
                for term in [
                    "pattern",
                    "patterns",
                    "clipart",
                    "clip art",
                    "digital",
                    "design",
                    "designs",
                    "fabric",
                    "paper",
                    "texture",
                    "background",
                    "wallpaper",
                ]:
                    title = re.sub(r"\b" + term + r"\b", "", title, flags=re.IGNORECASE)

                # Clean up again after removals
                title = re.sub(r"\s+", " ", title).strip()

                logger.info(f"Generated title: {title}")
                logger.info(f"DEBUG - Final processed title: {title}")

                # Clean up temporary file if it exists
                if image_path.endswith("_temp.png") or image_path.endswith("_temp.jpg"):
                    try:
                        os.remove(image_path)
                    except Exception as e:
                        logger.warning(
                            f"Failed to remove temporary file {image_path}: {e}"
                        )

                return title

            except Exception as e:
                logger.error(f"Error generating title with OpenRouter API: {e}")
                if attempt < max_retries:
                    logger.info(f"Retrying... ({attempt + 1}/{max_retries})")
                    # Wait before retrying
                    time.sleep(2 * (attempt + 1))  # Exponential backoff
                else:
                    # Clean up temporary file if it exists
                    if image_path.endswith("_temp.png") or image_path.endswith(
                        "_temp.jpg"
                    ):
                        try:
                            os.remove(image_path)
                        except Exception as e:
                            logger.warning(
                                f"Failed to remove temporary file {image_path}: {e}"
                            )
                    return None

        # If we get here, all retries failed
        return None

    def generate_content_from_image(
        self, image_path: str, instructions: str, max_retries: int = 2
    ) -> Dict[str, Any]:
        """
        Generate content (title, description, tags) from an image using OpenRouter API.

        Args:
            image_path: Path to the image file
            instructions: Instructions for the AI
            max_retries: Maximum number of retries on failure

        Returns:
            Dictionary with title, description, and tags
        """
        if not OPENAI_AVAILABLE:
            logger.error(
                "OpenAI package not available. Install with: pip install openai"
            )
            return {"title": "", "description": "", "tags": []}

        if not self.client:
            logger.error("OpenRouter client not initialized")
            return {"title": "", "description": "", "tags": []}

        if not os.path.exists(image_path):
            logger.error(f"Image file not found: {image_path}")
            return {"title": "", "description": "", "tags": []}

        try:
            # Load the image
            img = Image.open(image_path)
            logger.info(f"Successfully loaded image: {image_path}")

            # Get the image file size
            file_size_mb = os.path.getsize(image_path) / (1024 * 1024)
            logger.info(f"Image file size: {file_size_mb:.2f} MB")

            # Always resize the image to reduce API call time and improve reliability
            # Always resize for folder renaming to ensure fast API calls
            logger.info(f"Resizing image for API call")
            # Calculate new dimensions while maintaining aspect ratio
            max_dimension = 512  # Maximum dimension in pixels
            if img.width > img.height:
                new_width = min(img.width, max_dimension)
                new_height = int(img.height * (new_width / img.width))
            else:
                new_height = min(img.height, max_dimension)
                new_width = int(img.width * (new_height / img.height))

            # Resize the image
            img = img.resize((new_width, new_height), Image.LANCZOS)
            logger.info(f"Resized image to {new_width}x{new_height} for API call")

            # Save the resized image to a temporary file
            temp_path = (
                f"{image_path}_temp.{img.format.lower() if img.format else 'png'}"
            )
            img.save(temp_path)
            image_path = temp_path

            # Encode the image to base64
            base64_image = self._encode_image_to_base64(image_path)
            if not base64_image:
                return {"title": "", "description": "", "tags": []}

            # Create a system message to ensure consistent behavior
            system_message = "You are an Etsy marketing expert who specializes in creating compelling listings for digital products. You create SEO-optimized titles (130-140 characters), detailed descriptions with emoji section headers, and EXACTLY 13 strategic tags that help products rank well in Etsy search. Always format your response with clear 'Title:', 'Description:', and 'Tags:' sections. For tags, provide EXACTLY 13 unique tags, each under 20 characters, separated by commas. Do not repeat tags or use variations of the same tag. Focus on specific, relevant keywords that shoppers would use to find this type of digital product."

            # Create the messages
            messages = [
                {"role": "system", "content": system_message},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": instructions},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/{img.format.lower() if img.format else 'png'};base64,{base64_image}"
                            },
                        },
                    ],
                },
            ]

            # Try multiple times with increasing timeouts
            for attempt in range(max_retries + 1):
                # Generate content
                start_time = time.time()
                try:
                    # Log attempt information
                    logger.info(
                        f"Attempt {attempt + 1}/{max_retries + 1} to generate content with OpenRouter"
                    )

                    # Use a shorter timeout for the first attempt
                    current_timeout = max(5, self.timeout - (max_retries - attempt) * 3)
                    logger.info(
                        f"Using timeout of {current_timeout} seconds for this attempt"
                    )

                    response = self.client.chat.completions.create(
                        model=self.model_name,
                        messages=messages,
                        temperature=0.7,
                        max_tokens=1000,  # Limit token count to prevent long responses
                        timeout=current_timeout,
                    )
                    elapsed_time = time.time() - start_time
                    logger.info(f"API call completed in {elapsed_time:.2f} seconds")
                    break  # Success, exit the retry loop

                except Exception as e:
                    elapsed_time = time.time() - start_time
                    logger.error(
                        f"API call failed after {elapsed_time:.2f} seconds: {e}"
                    )

                    # If we've been waiting too long or on the last retry, log the error
                    if elapsed_time > 5 or attempt == max_retries:
                        logger.error(
                            f"API call failed after multiple attempts with model {self.model_name}"
                        )

                        # If this was the last retry, raise the error
                        if attempt == max_retries:
                            raise
                    elif attempt < max_retries:
                        # Wait before retrying with exponential backoff
                        wait_time = 2 * (attempt + 1)
                        logger.info(
                            f"Waiting {wait_time} seconds before retry {attempt + 2}..."
                        )
                        time.sleep(wait_time)
                    else:
                        raise

            # Clean up temporary file if it exists
            if image_path.endswith("_temp.png") or image_path.endswith("_temp.jpg"):
                try:
                    os.remove(image_path)
                except Exception as e:
                    logger.warning(f"Failed to remove temporary file {image_path}: {e}")

            # Check if the response is valid
            if not response.choices or not response.choices[0].message.content:
                logger.error("No content in OpenRouter response")

                # Try a simpler prompt as a fallback
                logger.info("Trying with a simpler prompt...")
                simpler_instructions = "Create an Etsy listing for this digital product with a title, description, and 13 tags. Keep it simple."
                simpler_messages = [
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that creates Etsy listings.",
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": simpler_instructions},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/{img.format.lower() if img.format else 'png'};base64,{base64_image}"
                                },
                            },
                        ],
                    },
                ]

                try:
                    logger.info("Attempting with simpler prompt...")
                    simpler_response = self.client.chat.completions.create(
                        model=self.model_name,
                        messages=simpler_messages,
                        temperature=0.7,
                        max_tokens=1000,
                        timeout=self.timeout,
                    )

                    if (
                        simpler_response.choices
                        and simpler_response.choices[0].message.content
                    ):
                        logger.info("Simpler prompt succeeded!")
                        response = simpler_response
                    else:
                        logger.error("Simpler prompt also returned empty content")
                        # Return empty content to signal failure
                        return {"title": "", "description": "", "tags": []}
                except Exception as e:
                    logger.error(f"Simpler prompt attempt failed: {e}")
                    # Return empty content to signal failure
                    return {"title": "", "description": "", "tags": []}

            # Get the raw response content
            raw_content = response.choices[0].message.content.strip()
            logger.info("Successfully received response from OpenRouter API")

            # Log the raw response for debugging
            logger.info(f"Raw OpenRouter API response:\n{raw_content}")

            # Process the response using our centralized utility function
            # Check if this is a thinking model based on the model name
            is_thinking_model = "thinking" in self.model_name.lower()
            content = process_ai_response(raw_content, is_thinking_model)

            logger.info(f"Processed OpenRouter API response:\n{content}")

            # Simple parsing to extract title, description, and tags
            logger.info("Parsing content from OpenRouter API response")

            title = ""
            description = ""
            tags = []

            # Basic extraction with regex
            # First try with "Title:" format
            title_match = re.search(
                r"Title:\s*(.+?)(?:\n|Description:)", content, re.DOTALL
            )
            if title_match:
                title = title_match.group(1).strip()
                # Remove any ** markers
                title = re.sub(r"^\*\*\s*", "", title)
                title = re.sub(r"\s*\*\*$", "", title)
                logger.info(f"Extracted title: {title}")
            else:
                logger.warning("Failed to extract title from OpenRouter API response")

            # Extract description
            desc_match = re.search(
                r"Description:\s*([\s\S]+?)(?:\n\s*Tags:|$)", content, re.DOTALL
            )
            if desc_match:
                description = desc_match.group(1).strip()
                logger.info(f"Extracted description with length: {len(description)}")
            else:
                logger.warning(
                    "Failed to extract description from OpenRouter API response"
                )

            # Extract tags
            tags_match = re.search(
                r"Tags:\s*(.+?)(?:\n\d{4}-\d{2}-\d{2}|$)", content, re.DOTALL
            )
            if tags_match:
                tags_text = tags_match.group(1).strip()
                # Split by comma and clean up
                raw_tags = [tag.strip() for tag in tags_text.split(",") if tag.strip()]

                # Deduplicate tags (case-insensitive)
                unique_tags = []
                seen_tags = set()
                for tag in raw_tags:
                    tag_lower = tag.lower()
                    if tag_lower not in seen_tags:
                        unique_tags.append(tag)
                        seen_tags.add(tag_lower)

                # Limit to exactly 13 tags
                if len(unique_tags) > 13:
                    logger.warning(
                        f"Too many tags ({len(unique_tags)}), limiting to 13"
                    )
                    tags = unique_tags[:13]
                elif len(unique_tags) < 13:
                    logger.warning(
                        f"Too few tags ({len(unique_tags)}), supplementing with generic tags"
                    )
                    tags = unique_tags
                    # Add generic tags to reach 13
                    generic_tags = [
                        "digital download",
                        "printable",
                        "instant download",
                        "digital art",
                        "digital design",
                        "commercial use",
                        "digital paper",
                        "scrapbooking",
                        "craft supply",
                        "digital clipart",
                        "digital pattern",
                        "digital background",
                        "etsy digital",
                        "digital print",
                        "digital file",
                    ]

                    # Only add tags that aren't already in our list (case-insensitive)
                    existing_tags_lower = {tag.lower() for tag in tags}
                    for tag in generic_tags:
                        if len(tags) >= 13:
                            break
                        if tag.lower() not in existing_tags_lower:
                            tags.append(tag)
                            existing_tags_lower.add(tag.lower())
                else:
                    tags = unique_tags

                # Validate tag length (Etsy has a 20 character limit)
                for i, tag in enumerate(tags):
                    if len(tag) > 20:
                        logger.warning(f"Tag '{tag}' exceeds 20 characters, truncating")
                        tags[i] = tag[:20]

                logger.info(f"Extracted {len(tags)} tags: {', '.join(tags)}")
            else:
                logger.warning("Failed to extract tags from OpenRouter API response")

            return {
                "title": title,
                "description": description,
                "tags": tags,
            }

        except Exception as e:
            logger.error(f"Error generating content from image: {e}")
            return {"title": "", "description": "", "tags": []}
