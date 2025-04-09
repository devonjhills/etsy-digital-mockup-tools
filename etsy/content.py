"""
Module for generating listing content with SEO optimization.
"""
import os
import json
import requests
from typing import Dict, List, Optional, Any, Tuple
import re

from utils.common import setup_logging

# Set up logging
logger = setup_logging(__name__)

class ContentGenerator:
    """Generate listing content with SEO optimization."""
    
    def __init__(self, api_key: str, api_url: Optional[str] = None):
        """
        Initialize the content generator.
        
        Args:
            api_key: API key for the LLM
            api_url: API URL for the LLM (optional)
        """
        self.api_key = api_key
        self.api_url = api_url or "https://api.openai.com/v1/chat/completions"
    
    def generate_title(self, 
                      product_info: Dict, 
                      template: Dict, 
                      max_length: int = 140) -> str:
        """
        Generate an SEO-optimized title for an Etsy listing.
        
        Args:
            product_info: Product information
            template: Template data
            max_length: Maximum title length
            
        Returns:
            Generated title
        """
        try:
            # Get the title template
            title_template = template.get("title_template", "")
            
            # Get SEO keywords
            seo_keywords = template.get("seo_keywords", [])
            
            # Create a prompt for the LLM
            prompt = f"""
            Generate an SEO-optimized title for an Etsy listing with the following information:
            
            Product Type: {template.get('product_type', '')}
            Product Name: {product_info.get('name', '')}
            
            The title should:
            1. Be catchy and appealing to potential buyers
            2. Include important keywords for SEO
            3. Be no longer than {max_length} characters
            4. Follow this template: {title_template}
            
            Important keywords to include: {', '.join(seo_keywords)}
            
            Additional product details:
            {json.dumps(product_info, indent=2)}
            
            Return ONLY the title, without any explanation or additional text.
            """
            
            # Call the LLM API
            title = self._call_llm_api(prompt)
            
            # Ensure the title is not too long
            if len(title) > max_length:
                title = title[:max_length-3] + "..."
            
            return title
        except Exception as e:
            logger.error(f"Error generating title: {e}")
            
            # Fallback: Use the template with basic substitution
            try:
                title_template = template.get("title_template", "{name}")
                title = title_template.format(
                    name=product_info.get("name", "Product"),
                    **product_info
                )
                
                # Ensure the title is not too long
                if len(title) > max_length:
                    title = title[:max_length-3] + "..."
                
                return title
            except Exception as fallback_error:
                logger.error(f"Error with fallback title generation: {fallback_error}")
                return product_info.get("name", "Product")
    
    def generate_description(self, 
                           product_info: Dict, 
                           template: Dict) -> str:
        """
        Generate an SEO-optimized description for an Etsy listing.
        
        Args:
            product_info: Product information
            template: Template data
            
        Returns:
            Generated description
        """
        try:
            # Get the description template
            description_template = template.get("description_template", "")
            
            # Get SEO keywords
            seo_keywords = template.get("seo_keywords", [])
            
            # Create a prompt for the LLM
            prompt = f"""
            Generate an SEO-optimized description for an Etsy listing with the following information:
            
            Product Type: {template.get('product_type', '')}
            Product Name: {product_info.get('name', '')}
            
            The description should:
            1. Be detailed and informative
            2. Include important keywords for SEO
            3. Be formatted with Markdown for readability
            4. Follow this template: {description_template}
            
            Important keywords to include: {', '.join(seo_keywords)}
            
            Additional product details:
            {json.dumps(product_info, indent=2)}
            
            Return ONLY the description, formatted with Markdown, without any explanation or additional text.
            """
            
            # Call the LLM API
            description = self._call_llm_api(prompt)
            
            return description
        except Exception as e:
            logger.error(f"Error generating description: {e}")
            
            # Fallback: Use the template with basic substitution
            try:
                description_template = template.get("description_template", "# {name}\n\nDigital product for download.")
                description = description_template.format(
                    name=product_info.get("name", "Product"),
                    **product_info
                )
                
                return description
            except Exception as fallback_error:
                logger.error(f"Error with fallback description generation: {fallback_error}")
                return f"# {product_info.get('name', 'Product')}\n\nDigital product for download."
    
    def generate_tags(self, 
                     product_info: Dict, 
                     template: Dict, 
                     max_tags: int = 13) -> List[str]:
        """
        Generate SEO-optimized tags for an Etsy listing.
        
        Args:
            product_info: Product information
            template: Template data
            max_tags: Maximum number of tags
            
        Returns:
            List of generated tags
        """
        try:
            # Get template tags
            template_tags = template.get("tags", [])
            
            # If we have enough tags in the template, use those
            if len(template_tags) >= max_tags:
                return template_tags[:max_tags]
            
            # Get SEO keywords
            seo_keywords = template.get("seo_keywords", [])
            
            # Create a prompt for the LLM
            prompt = f"""
            Generate SEO-optimized tags for an Etsy listing with the following information:
            
            Product Type: {template.get('product_type', '')}
            Product Name: {product_info.get('name', '')}
            
            The tags should:
            1. Be relevant to the product
            2. Include important keywords for SEO
            3. Be no more than 20 characters each
            4. Be no more than {max_tags} tags total
            
            Important keywords to include: {', '.join(seo_keywords)}
            
            Additional product details:
            {json.dumps(product_info, indent=2)}
            
            Return ONLY a comma-separated list of tags, without any explanation or additional text.
            """
            
            # Call the LLM API
            tags_text = self._call_llm_api(prompt)
            
            # Parse the tags
            tags = [tag.strip() for tag in tags_text.split(',')]
            
            # Ensure tags are not too long
            tags = [tag[:20] for tag in tags if tag]
            
            # Limit to max_tags
            tags = tags[:max_tags]
            
            return tags
        except Exception as e:
            logger.error(f"Error generating tags: {e}")
            
            # Fallback: Use the template tags
            return template_tags[:max_tags]
    
    def _call_llm_api(self, prompt: str) -> str:
        """
        Call the LLM API with the given prompt.
        
        Args:
            prompt: Prompt for the LLM
            
        Returns:
            LLM response
        """
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            data = {
                "model": "gpt-4",
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant that generates SEO-optimized content for Etsy listings."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 1000
            }
            
            response = requests.post(self.api_url, headers=headers, json=data)
            
            if response.status_code == 200:
                response_data = response.json()
                return response_data['choices'][0]['message']['content'].strip()
            else:
                logger.error(f"Error calling LLM API: {response.status_code} {response.text}")
                return ""
        except Exception as e:
            logger.error(f"Error calling LLM API: {e}")
            return ""
