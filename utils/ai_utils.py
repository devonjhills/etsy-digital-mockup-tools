"""AI provider utilities and response processing."""

import os
import re
from typing import Optional, Dict, Any

# Set up logging
from utils.common import setup_logging
from utils.env_loader import load_environment

logger = setup_logging(__name__)

# Load environment variables
load_environment()


def get_ai_provider(provider_name: str = "gemini", api_key: Optional[str] = None) -> Optional[Any]:
    """Get an AI provider instance.
    
    Args:
        provider_name: Name of the AI provider ("gemini" or "openai")
        api_key: Optional API key to use (if not provided, will try environment)
        
    Returns:
        AI provider instance or None if not available
    """
    try:
        logger.info(f"Attempting to create AI provider: {provider_name}, API key provided: {api_key is not None}")
        
        if provider_name.lower() == "gemini":
            if not api_key:
                api_key = os.getenv("GEMINI_API_KEY")
                logger.info(f"Retrieved Gemini API key from environment: {api_key is not None}")
            if not api_key:
                logger.warning("GEMINI_API_KEY not found in environment or provided")
                return None
            
            from ai_providers.gemini_provider import GeminiProvider
            provider = GeminiProvider(api_key=api_key)
            logger.info(f"Created Gemini provider successfully: {provider is not None}")
            return provider
            
        elif provider_name.lower() == "openai":
            if not api_key:
                api_key = os.getenv("OPENAI_API_KEY")
                logger.info(f"Retrieved OpenAI API key from environment: {api_key is not None}")
            if not api_key:
                logger.warning("OPENAI_API_KEY not found in environment or provided")
                return None
            
            from ai_providers.openai_provider import OpenAIProvider
            provider = OpenAIProvider(api_key=api_key)
            logger.info(f"Created OpenAI provider successfully: {provider is not None}")
            return provider
            
        else:
            logger.error(f"Unknown AI provider: {provider_name}")
            return None
            
    except ImportError as e:
        logger.error(f"Failed to import AI provider {provider_name}: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to create AI provider {provider_name}: {e}")
        return None


def get_available_providers() -> Dict[str, bool]:
    """Get available AI providers and their status.
    
    Returns:
        Dict mapping provider names to availability status
    """
    providers = {}
    
    # Check Gemini
    providers["gemini"] = bool(os.getenv("GEMINI_API_KEY"))
    
    # Check OpenAI
    providers["openai"] = bool(os.getenv("OPENAI_API_KEY"))
    
    return providers


def extract_thinking_model_response(response_text: str) -> str:
    """
    Extract the final answer from a thinking model's response.

    This function handles responses from models like moonshotai/kimi-vl-a3b-thinking:free
    that include their thinking process with markers like ◁think▷ and ◁/think▷.

    Args:
        response_text: The raw response text from the model

    Returns:
        The extracted final answer, with thinking process removed
    """
    # Log the raw response for debugging
    logger.info(f"Processing thinking model response of length {len(response_text)}")

    # Check if this is a thinking model response
    has_thinking_markers = "◁think▷" in response_text
    logger.info(f"Has thinking markers: {has_thinking_markers}")

    if not has_thinking_markers:
        # If there are no thinking markers, return the original response
        return response_text.strip()

    # The simplest approach: get everything after the last ◁/think▷ marker
    think_end_token = "◁/think▷"

    if think_end_token in response_text:
        # Split by the end token and take the last part (the actual answer)
        original_response = response_text
        final_answer = response_text.split(think_end_token)[-1].strip()
        logger.info(f"Extracted answer after thinking marker: {final_answer[:50]}...")

        # If the extracted answer is empty, try to extract the last sentence from the thinking
        if not final_answer.strip():
            logger.info(
                "Extracted answer is empty, trying to get last sentence from thinking"
            )
            # Get the thinking part (everything before the last ◁/think▷)
            thinking_part = original_response.split(think_end_token)[0]
            # Extract the last sentence from the thinking
            sentences = re.split(r"[.!?]\s+", thinking_part)
            if sentences:
                final_answer = sentences[-1].strip()
                logger.info(
                    f"Extracted last sentence from thinking: {final_answer[:50]}..."
                )
    else:
        # If there's no end token but there is a start token, the model might have been cut off
        # In this case, we'll try to extract a meaningful response from the thinking content
        logger.info("No thinking end token found, model response may be incomplete")

        # Extract the thinking content
        thinking_content = re.search(r"◁think▷(.+)$", response_text, flags=re.DOTALL)
        if thinking_content:
            thinking_text = thinking_content.group(1).strip()
            logger.info(f"Extracted thinking content: {thinking_text[:50]}...")

            # Look for numbered options or lists in the thinking
            options = re.findall(r"\d+\.\s*([^\n\d]+)(?:\n|$)", thinking_text)
            if options:
                # Take the first option that's 2-3 words
                for option in options:
                    option = option.strip()
                    if 1 <= len(option.split()) <= 3:
                        final_answer = option
                        logger.info(f"Selected option from thinking: {final_answer}")
                        break
                else:
                    # If no good option found, take the first one anyway
                    final_answer = options[0].strip()
                    logger.info(f"Using first option from thinking: {final_answer}")
            else:
                # Look for the last complete sentence in the thinking
                sentences = re.split(r"[.!?]\s+", thinking_text)
                if sentences:
                    # Find the last sentence that has 1-3 words and doesn't contain prohibited terms
                    prohibited_terms = ["pattern", "clipart", "digital", "design"]
                    for sentence in reversed(sentences):
                        sentence = sentence.strip()
                        words = sentence.split()
                        if 1 <= len(words) <= 3 and not any(
                            term.lower() in sentence.lower()
                            for term in prohibited_terms
                        ):
                            final_answer = sentence
                            logger.info(
                                f"Using last suitable sentence from thinking: {final_answer}"
                            )
                            break
                    else:
                        # If no suitable sentence found, extract 2-3 words from the last sentence
                        last_sentence = sentences[-1].strip()
                        words = last_sentence.split()
                        final_answer = " ".join(words[: min(3, len(words))])
                        logger.info(
                            f"Extracted words from last sentence: {final_answer}"
                        )
                else:
                    # If we couldn't extract sentences, just remove the thinking marker
                    final_answer = re.sub(
                        r"◁think▷.*", "", response_text, flags=re.DOTALL
                    ).strip()
        else:
            # If we couldn't extract thinking content, remove the thinking marker
            final_answer = re.sub(
                r"◁think▷.*", "", response_text, flags=re.DOTALL
            ).strip()
            logger.info(f"After removing thinking marker: {final_answer[:50]}...")

    # Clean up the final answer
    final_answer = re.sub(r'["\']', "", final_answer)  # Remove quotes
    final_answer = re.sub(
        r"◁.*?▷", "", final_answer
    )  # Remove any remaining markers like ◁answer▷
    final_answer = re.sub(
        r"<.*?>", "", final_answer
    )  # Remove any remaining HTML-like tags
    final_answer = re.sub(
        r"\s+", " ", final_answer
    )  # Replace multiple spaces with a single space
    final_answer = final_answer.strip()  # Remove leading/trailing spaces

    # Handle cases where multiple items are returned despite our instructions
    # Check for multiple lines
    if "\n" in final_answer:
        logger.warning("Multiple lines detected in answer, taking only the first line")
        final_answer = final_answer.split("\n")[0].strip()

    # Check for numbered options (e.g., "1. Title One")
    if re.search(r"^\d+\.\s", final_answer):
        logger.warning("Numbered option detected in answer, removing the number")
        final_answer = re.sub(r"^\d+\.\s", "", final_answer).strip()

    # Check for "or" or similar conjunctions that might indicate multiple options
    if re.search(r"\b(or|and|vs|versus)\b", final_answer, re.IGNORECASE):
        logger.warning(
            "Multiple options detected in answer, taking only the first part"
        )
        final_answer = re.split(
            r"\b(or|and|vs|versus)\b", final_answer, flags=re.IGNORECASE
        )[0].strip()

    return final_answer


def process_ai_response(response_text: str, is_thinking_model: bool = False) -> str:
    """
    Process an AI model response, handling thinking models if needed.

    Args:
        response_text: The raw response text from the model
        is_thinking_model: Whether the response is from a thinking model

    Returns:
        The processed response text
    """
    if not response_text:
        return ""

    # If this is a thinking model or contains thinking markers, extract the final answer
    if is_thinking_model or "◁think▷" in response_text:
        return extract_thinking_model_response(response_text)

    # Otherwise, return the original response
    return response_text.strip()


def generate_content_with_ai(ai_provider: Any, prompt: str, image_path: str = None) -> str:
    """Generate content using AI provider.
    
    Args:
        ai_provider: AI provider instance
        prompt: Text prompt for generation
        image_path: Optional path to image for analysis
        
    Returns:
        Generated content string
    """
    if not ai_provider:
        logger.warning("No AI provider available for content generation")
        return ""
    
    try:
        if image_path and os.path.exists(image_path):
            response = ai_provider.analyze_image_with_prompt(image_path, prompt)
        else:
            response = ai_provider.generate_text(prompt)
        
        return process_ai_response(response)
        
    except Exception as e:
        logger.error(f"AI content generation failed: {e}")
        return ""
