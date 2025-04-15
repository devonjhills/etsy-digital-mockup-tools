"""
Module for creating and managing Etsy listings.
"""

import os
import json
import requests
from typing import Dict, List, Optional, Any, Tuple
import time

from utils.common import setup_logging
from etsy.auth import EtsyAuth

# Set up logging
logger = setup_logging(__name__)


class EtsyListings:
    """Create and manage Etsy listings."""

    def __init__(self, auth: EtsyAuth):
        """
        Initialize the Etsy listings handler.

        Args:
            auth: Etsy authentication handler
        """
        self.auth = auth
        self.base_url = "https://openapi.etsy.com/v3"
        self.shop_id = self._get_shop_id()

    def _get_shop_id(self) -> Optional[str]:
        """
        Get the shop ID.

        Returns:
            Shop ID or None if not found
        """
        # First try to get the shop ID from environment variables
        shop_id = os.environ.get("ETSY_SHOP_ID")
        if shop_id:
            logger.info(f"Using shop ID from environment: {shop_id}")
            return shop_id

        # Fall back to the hardcoded shop ID if environment variable is not set
        logger.info("Using default shop ID: 42865309")
        return "42865309"

        # Uncomment this code if you want to fetch the shop ID dynamically instead
        # try:
        #     url = f"{self.base_url}/application/shops"
        #     headers = self.auth.get_headers()
        #
        #     response = requests.get(url, headers=headers)
        #
        #     if response.status_code == 200:
        #         data = response.json()
        #         if data.get('count', 0) > 0:
        #             return data['results'][0]['shop_id']
        #         else:
        #             logger.error("No shops found.")
        #             return None
        #     else:
        #         logger.error(f"Error getting shop ID: {response.status_code} {response.text}")
        #         return None
        # except Exception as e:
        #     logger.error(f"Error getting shop ID: {e}")
        #     return None

    def create_listing(
        self,
        title: str,
        description: str,
        price: float,
        quantity: int,
        tags: List[str],
        materials: List[str],
        taxonomy_id: int,
        shipping_profile_id: Optional[int] = None,
        shop_section_id: Optional[int] = None,
        who_made: str = "i_did",
        is_supply: bool = False,
        when_made: str = "made_to_order",
        is_digital: bool = True,
        is_personalizable: bool = False,
        personalization_instructions: str = "",
        is_draft: bool = False,
    ) -> Optional[Dict]:
        """
        Create a new Etsy listing.

        Args:
            title: Listing title
            description: Listing description
            price: Listing price
            quantity: Listing quantity
            tags: Listing tags
            materials: Listing materials
            shipping_profile_id: Shipping profile ID
            shop_section_id: Shop section ID
            taxonomy_id: Taxonomy ID
            who_made: Who made the item
            is_supply: Whether the item is a supply
            when_made: When the item was made
            is_digital: Whether the item is digital
            is_personalizable: Whether the item is personalizable
            personalization_instructions: Personalization instructions
            is_draft: Whether to create the listing as a draft

        Returns:
            Listing data or None if creation failed
        """
        if not self.shop_id:
            logger.error("No shop ID available.")
            return None

        try:
            url = f"{self.base_url}/application/shops/{self.shop_id}/listings"
            headers = self.auth.get_headers()

            # Prepare the data
            data = {
                "quantity": quantity,
                "title": title,
                "description": description,
                "price": price,
                "who_made": who_made,
                "when_made": when_made,
                "taxonomy_id": taxonomy_id,
                "state": "draft" if is_draft else "active",
                "is_digital": is_digital,
                "type": (
                    "download" if is_digital else "physical"
                ),  # Explicitly set type for digital listings
                "is_personalizable": is_personalizable,
                "personalization_is_required": is_personalizable,
                "personalization_instructions": (
                    personalization_instructions if is_personalizable else ""
                ),
                "is_supply": is_supply,
                "tags": tags[:13],  # Etsy allows max 13 tags
                "materials": materials[:13],  # Etsy allows max 13 materials
            }

            # Add shipping_profile_id only if provided (required for physical products)
            if shipping_profile_id is not None:
                data["shipping_profile_id"] = shipping_profile_id

            # Add shop_section_id if provided
            if shop_section_id is not None:
                data["shop_section_id"] = shop_section_id

            response = requests.post(url, headers=headers, json=data)

            if response.status_code == 201:
                listing_data = response.json()
                logger.info(f"Listing created: {listing_data['listing_id']}")
                return listing_data
            else:
                logger.error(
                    f"Error creating listing: {response.status_code} {response.text}"
                )
                return None
        except Exception as e:
            logger.error(f"Error creating listing: {e}")
            return None

    def upload_listing_image(
        self, listing_id: int, image_path: str, rank: int = 1
    ) -> Optional[Dict]:
        """
        Upload an image to a listing.

        Args:
            listing_id: Listing ID
            image_path: Path to the image
            rank: Image rank

        Returns:
            Image data or None if upload failed
        """
        if not self.shop_id:
            logger.error("No shop ID available.")
            return None

        try:
            # First, get an upload token
            url = f"{self.base_url}/application/shops/{self.shop_id}/listings/{listing_id}/images"
            headers = self.auth.get_headers()

            with open(image_path, "rb") as f:
                files = {"image": (os.path.basename(image_path), f, "image/jpeg")}

                data = {"rank": rank}

                # Remove Content-Type header for file upload
                upload_headers = self.auth.get_headers()
                if "Content-Type" in upload_headers:
                    del upload_headers["Content-Type"]

                response = requests.post(
                    url, headers=upload_headers, data=data, files=files
                )

                if response.status_code == 201:
                    image_data = response.json()
                    logger.info(f"Image uploaded: {image_data['listing_image_id']}")
                    return image_data
                else:
                    logger.error(
                        f"Error uploading image: {response.status_code} {response.text}"
                    )
                    return None
        except Exception as e:
            logger.error(f"Error uploading image: {e}")
            return None

    def upload_digital_file(
        self, listing_id: int, file_path: str, rank: int = 0
    ) -> Optional[Dict]:
        """
        Upload a digital file to a listing.

        Args:
            listing_id: Listing ID
            file_path: Path to the file
            rank: File rank (default: 0)

        Returns:
            File data or None if upload failed
        """
        if not self.shop_id:
            logger.error("No shop ID available.")
            return None

        try:
            url = f"{self.base_url}/application/shops/{self.shop_id}/listings/{listing_id}/files"

            with open(file_path, "rb") as f:
                file_content = f.read()

                # Remove Content-Type header for file upload
                upload_headers = self.auth.get_headers()
                if "Content-Type" in upload_headers:
                    del upload_headers["Content-Type"]

                file_data = {"name": os.path.basename(file_path), "rank": rank}

                response = requests.post(
                    url,
                    headers=upload_headers,
                    files={
                        "file": (
                            os.path.basename(file_path),
                            file_content,
                            "multipart/form-data",
                        )
                    },
                    data=file_data,
                )

                if response.status_code == 201:
                    file_data = response.json()
                    logger.info(
                        f"Digital file uploaded: {file_data['listing_file_id']}"
                    )
                    return file_data
                else:
                    logger.error(
                        f"Error uploading digital file: {response.status_code} {response.text}"
                    )
                    return None
        except Exception as e:
            logger.error(f"Error uploading digital file: {e}")
            return None

    def upload_video(
        self, listing_id: int, video_path: str, rank: int = 1
    ) -> Optional[Dict]:
        """
        Upload a video to a listing.

        Args:
            listing_id: Listing ID
            video_path: Path to the video
            rank: Video rank

        Returns:
            Video data or None if upload failed
        """
        if not self.shop_id:
            logger.error("No shop ID available.")
            return None

        try:
            url = f"{self.base_url}/application/shops/{self.shop_id}/listings/{listing_id}/videos"

            with open(video_path, "rb") as f:
                video_content = f.read()

                # Remove Content-Type header for file upload
                upload_headers = self.auth.get_headers()
                if "Content-Type" in upload_headers:
                    del upload_headers["Content-Type"]

                video_data = {"name": os.path.basename(video_path), "rank": rank}

                response = requests.post(
                    url,
                    headers=upload_headers,
                    files={
                        "video": (
                            os.path.basename(video_path),
                            video_content,
                            "multipart/form-data",
                        )
                    },
                    data=video_data,
                )

                if response.status_code == 201:
                    video_data = response.json()
                    logger.info(f"Video uploaded: {video_data.get('listing_video_id')}")
                    return video_data
                else:
                    logger.error(
                        f"Error uploading video: {response.status_code} {response.text}"
                    )
                    return None
        except Exception as e:
            logger.error(f"Error uploading video: {e}")
            return None

    def update_listing(self, listing_id: int, **kwargs) -> Optional[Dict]:
        """
        Update an existing listing.

        Args:
            listing_id: Listing ID
            **kwargs: Fields to update

        Returns:
            Updated listing data or None if update failed
        """
        if not self.shop_id:
            logger.error("No shop ID available.")
            return None

        try:
            url = f"{self.base_url}/application/shops/{self.shop_id}/listings/{listing_id}"
            headers = self.auth.get_headers()

            response = requests.put(url, headers=headers, json=kwargs)

            if response.status_code == 200:
                listing_data = response.json()
                logger.info(f"Listing updated: {listing_data['listing_id']}")
                return listing_data
            else:
                logger.error(
                    f"Error updating listing: {response.status_code} {response.text}"
                )
                return None
        except Exception as e:
            logger.error(f"Error updating listing: {e}")
            return None

    def get_listing(self, listing_id: int) -> Optional[Dict]:
        """
        Get a listing by ID.

        Args:
            listing_id: Listing ID

        Returns:
            Listing data or None if not found
        """
        if not self.shop_id:
            logger.error("No shop ID available.")
            return None

        try:
            url = f"{self.base_url}/application/listings/{listing_id}"
            headers = self.auth.get_headers()

            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                listing_data = response.json()
                return listing_data
            else:
                logger.error(
                    f"Error getting listing: {response.status_code} {response.text}"
                )
                return None
        except Exception as e:
            logger.error(f"Error getting listing: {e}")
            return None

    def delete_listing(self, listing_id: int) -> bool:
        """
        Delete a listing.

        Args:
            listing_id: Listing ID

        Returns:
            True if deletion was successful, False otherwise
        """
        if not self.shop_id:
            logger.error("No shop ID available.")
            return False

        try:
            url = f"{self.base_url}/application/listings/{listing_id}"
            headers = self.auth.get_headers()

            response = requests.delete(url, headers=headers)

            if response.status_code == 204:
                logger.info(f"Listing deleted: {listing_id}")
                return True
            else:
                logger.error(
                    f"Error deleting listing: {response.status_code} {response.text}"
                )
                return False
        except Exception as e:
            logger.error(f"Error deleting listing: {e}")
            return False

    def get_shipping_profiles(self) -> Optional[List[Dict]]:
        """
        Get shipping profiles.

        Returns:
            List of shipping profiles or None if not found
        """
        if not self.shop_id:
            logger.error("No shop ID available.")
            return None

        try:
            url = f"{self.base_url}/application/shops/{self.shop_id}/shipping-profiles"
            headers = self.auth.get_headers()

            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                data = response.json()
                return data.get("results", [])
            else:
                logger.error(
                    f"Error getting shipping profiles: {response.status_code} {response.text}"
                )
                return None
        except Exception as e:
            logger.error(f"Error getting shipping profiles: {e}")
            return None

    def get_taxonomies(self) -> Optional[List[Dict]]:
        """
        Get taxonomies.

        Returns:
            List of taxonomies or None if not found
        """
        try:
            url = f"{self.base_url}/application/seller-taxonomy/nodes"
            headers = self.auth.get_headers()

            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                data = response.json()
                return data.get("results", [])
            else:
                logger.error(
                    f"Error getting taxonomies: {response.status_code} {response.text}"
                )
                return None
        except Exception as e:
            logger.error(f"Error getting taxonomies: {e}")
            return None

    def get_properties_by_taxonomy_id(self, taxonomy_id: int) -> Optional[List[Dict]]:
        """
        Get properties for a specific taxonomy ID.

        Args:
            taxonomy_id: Taxonomy ID

        Returns:
            List of properties or None if not found
        """
        try:
            url = f"{self.base_url}/application/seller-taxonomy/nodes/{taxonomy_id}/properties"
            headers = self.auth.get_headers()

            logger.info(f"Fetching properties for taxonomy ID: {taxonomy_id}")
            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                data = response.json()
                properties = data.get("results", [])

                # Log the properties for debugging
                logger.info(
                    f"Found {len(properties)} properties for taxonomy {taxonomy_id}"
                )
                for prop in properties:
                    prop_name = prop.get("name", "")
                    prop_id = prop.get("property_id")
                    logger.info(f"Property: {prop_name} (ID: {prop_id})")

                    # Log available values if present
                    if "possible_values" in prop and prop["possible_values"]:
                        value_names = [
                            v.get("name", "") for v in prop["possible_values"][:5]
                        ]
                        logger.info(
                            f"  Available values: {', '.join(value_names)}{'...' if len(prop['possible_values']) > 5 else ''}"
                        )

                return properties
            else:
                logger.error(
                    f"Error getting properties: {response.status_code} {response.text}"
                )
                return None
        except Exception as e:
            logger.error(f"Error getting properties: {e}")
            return None

    def update_listing_properties(
        self, listing_id: int, property_values: List[Dict]
    ) -> Optional[Dict]:
        """
        Update listing properties.

        Args:
            listing_id: Listing ID
            property_values: List of property values to set
                Each property value should have:
                - property_id: ID of the property
                - value_ids: List of value IDs
                - values: List of string values
                - scale_id: Scale ID (optional)

        Returns:
            Updated listing data or None if update failed
        """
        if not self.shop_id:
            logger.error("No shop ID available.")
            return None

        try:
            # Instead of using a dedicated properties endpoint, we'll use the main listing update endpoint
            # with the properties field
            url = f"{self.base_url}/application/shops/{self.shop_id}/listings/{listing_id}"
            headers = self.auth.get_headers()

            # Format the property values for the API
            formatted_properties = []
            for prop in property_values:
                formatted_prop = {
                    "property_id": prop["property_id"],
                    "value_ids": prop.get("value_ids", []),
                    "values": prop.get("values", []),
                }

                if "scale_id" in prop and prop["scale_id"]:
                    formatted_prop["scale_id"] = prop["scale_id"]

                formatted_properties.append(formatted_prop)

            # Use the main listing update endpoint with the properties field
            data = {"properties": formatted_properties}

            # Use PUT for updating the listing
            response = requests.put(url, headers=headers, json=data)

            if response.status_code == 200:
                property_data = response.json()
                logger.info(f"Listing properties updated for listing: {listing_id}")
                return property_data
            else:
                logger.error(
                    f"Error updating listing properties: {response.status_code} {response.text}"
                )
                return None
        except Exception as e:
            logger.error(f"Error updating listing properties: {e}")
            return None

    def get_listing_inventory(self, listing_id: int) -> Optional[Dict]:
        """
        Get inventory for a listing.

        Args:
            listing_id: Listing ID

        Returns:
            Inventory data or None if not found
        """
        if not self.shop_id:
            logger.error("No shop ID available.")
            return None

        try:
            url = f"{self.base_url}/application/listings/{listing_id}/inventory"
            headers = self.auth.get_headers()

            logger.info(f"Getting inventory for listing {listing_id}")
            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                inventory_data = response.json()
                logger.info(
                    f"Successfully retrieved inventory for listing {listing_id}"
                )
                return inventory_data
            else:
                logger.error(
                    f"Error getting listing inventory: {response.status_code} {response.text}"
                )
                return None
        except Exception as e:
            logger.error(f"Error getting listing inventory: {e}")
            return None

    def update_listing_inventory(
        self,
        listing_id: int,
        products: List[Dict],
        price_on_property: List[int] = [],
        quantity_on_property: List[int] = [],
        sku_on_property: List[int] = [],
    ) -> Optional[Dict]:
        """
        Update listing inventory with property values.

        Args:
            listing_id: Listing ID
            products: List of products with property values
                Each product should have:
                - sku: SKU for the product
                - property_values: List of property values
                - offerings: List of offerings (price, quantity)
            price_on_property: List of property IDs that affect price
            quantity_on_property: List of property IDs that affect quantity
            sku_on_property: List of property IDs that affect SKU

        Returns:
            Updated inventory data or None if update failed
        """
        if not self.shop_id:
            logger.error("No shop ID available.")
            return None

        try:
            url = f"{self.base_url}/application/listings/{listing_id}/inventory"
            headers = self.auth.get_headers()

            data = {
                "products": products,
                "price_on_property": price_on_property,
                "quantity_on_property": quantity_on_property,
                "sku_on_property": sku_on_property,
            }

            logger.info(
                f"Updating inventory for listing {listing_id} with {len(products)} products"
            )
            logger.debug(f"Request data: {data}")

            response = requests.put(url, headers=headers, json=data)

            if response.status_code == 200:
                inventory_data = response.json()
                logger.info(f"Listing inventory updated for listing: {listing_id}")
                return inventory_data
            else:
                logger.error(
                    f"Error updating listing inventory: {response.status_code} {response.text}"
                )
                return None
        except Exception as e:
            logger.error(f"Error updating listing inventory: {e}")
            return None

    def set_listing_attributes(
        self, listing_id: int, product_type: str, attributes: Dict[str, Any]
    ) -> bool:
        # Note: product_type parameter is kept for backward compatibility
        """
        Set listing attributes like craft type, color, dimensions, etc.

        Args:
            listing_id: Listing ID
            product_type: Type of product (pattern, clipart, etc.)
            attributes: Dictionary of attributes to set
                Can include:
                - craft_types: List of craft types
                - primary_color: Primary color
                - secondary_color: Secondary color
                - length: Length value
                - width: Width value
                - length_unit: Unit for length (inches, cm, etc.)
                - width_unit: Unit for width (inches, cm, etc.)
                - occasion: Occasion
                - holiday: Holiday
                - subject: List of subjects

        Returns:
            True if attributes were set successfully, False otherwise
        """
        if not self.shop_id:
            logger.error("No shop ID available.")
            return False

        try:
            # Get the listing to confirm taxonomy_id
            listing = self.get_listing(listing_id)
            if not listing:
                logger.error(f"Could not get listing {listing_id}")
                return False

            taxonomy_id = listing.get("taxonomy_id")
            if not taxonomy_id:
                logger.error(f"Listing {listing_id} has no taxonomy_id")
                return False

            # Get available properties for this taxonomy
            properties = self.get_properties_by_taxonomy_id(taxonomy_id)
            if not properties:
                logger.error(f"Could not get properties for taxonomy {taxonomy_id}")
                return False

            # Log available properties for debugging
            logger.info(
                f"Found {len(properties)} properties for taxonomy {taxonomy_id}"
            )
            for prop in properties:
                logger.info(
                    f"Property: {prop.get('name')} (ID: {prop.get('property_id')})"
                )

            # Map attribute names to property IDs
            property_map = {}
            for prop in properties:
                prop_name = prop.get("name", "").lower()

                # Log property details for debugging
                logger.info(
                    f"Found property: {prop.get('name')} (ID: {prop.get('property_id')})"
                )

                # Check if this property has possible values
                if "possible_values" in prop and prop["possible_values"]:
                    logger.info(
                        f"  Available values: {', '.join([v.get('name', '') for v in prop['possible_values'][:5]])}{'...' if len(prop['possible_values']) > 5 else ''}"
                    )

                # Map properties to our attribute keys
                if "craft" in prop_name or "type" in prop_name:
                    property_map["craft_type"] = prop
                elif "color" in prop_name and "primary" in prop_name:
                    property_map["primary_color"] = prop
                elif "color" in prop_name and "secondary" in prop_name:
                    property_map["secondary_color"] = prop
                elif prop_name in ["length", "width", "height"]:
                    property_map[prop_name] = prop
                elif "occasion" in prop_name:
                    property_map["occasion"] = prop
                elif "holiday" in prop_name:
                    property_map["holiday"] = prop
                elif "subject" in prop_name or "theme" in prop_name:
                    property_map["subject"] = prop

            # Prepare property values to update
            property_values = []

            # Add craft types
            if "craft_type" in property_map and "craft_types" in attributes:
                craft_prop = property_map["craft_type"]
                craft_values = []
                craft_value_ids = []

                # Get all available craft type values
                available_craft_types = craft_prop.get("possible_values", [])
                logger.info(f"Available craft types: {len(available_craft_types)}")

                # Try to match craft types to available values
                for craft_type in attributes["craft_types"]:
                    found = False
                    best_match = None
                    best_match_id = None

                    # Log what we're looking for
                    logger.info(f"Looking for craft type match for: {craft_type}")

                    # First try exact match
                    for value in available_craft_types:
                        value_name = value.get("name", "")
                        if craft_type.lower() == value_name.lower():
                            craft_value_ids.append(value.get("value_id"))
                            craft_values.append(value_name)
                            found = True
                            logger.info(f"  Found exact match: {value_name}")
                            break

                    # If no exact match, try partial match
                    if not found:
                        for value in available_craft_types:
                            value_name = value.get("name", "")
                            if (
                                craft_type.lower() in value_name.lower()
                                or value_name.lower() in craft_type.lower()
                            ):
                                best_match = value_name
                                best_match_id = value.get("value_id")
                                logger.info(f"  Found partial match: {value_name}")
                                break

                        if best_match:
                            craft_value_ids.append(best_match_id)
                            craft_values.append(best_match)
                            found = True

                    # If still no match, skip this craft type
                    if not found:
                        logger.warning(f"  No match found for craft type: {craft_type}")

                if craft_values:
                    property_values.append(
                        {
                            "property_id": craft_prop.get("property_id"),
                            "property_name": craft_prop.get("name"),
                            "value_ids": craft_value_ids,
                            "values": craft_values,
                            "scale_id": craft_prop.get("scale_id"),
                        }
                    )

            # Add primary color
            if "primary_color" in property_map and "primary_color" in attributes:
                color_prop = property_map["primary_color"]
                color_value = attributes["primary_color"]
                color_value_id = None

                # Get all available color values
                available_colors = color_prop.get("possible_values", [])
                logger.info(f"Available colors: {len(available_colors)}")
                logger.info(f"Looking for color match for: {color_value}")

                # First try exact match
                for value in available_colors:
                    value_name = value.get("name", "")
                    if color_value.lower() == value_name.lower():
                        color_value_id = value.get("value_id")
                        color_value = value_name
                        logger.info(f"  Found exact color match: {value_name}")
                        break

                # If no exact match, try partial match
                if not color_value_id:
                    for value in available_colors:
                        value_name = value.get("name", "")
                        if (
                            color_value.lower() in value_name.lower()
                            or value_name.lower() in color_value.lower()
                        ):
                            color_value_id = value.get("value_id")
                            color_value = value_name
                            logger.info(f"  Found partial color match: {value_name}")
                            break

                # If still no match, use a default color like "Multi-color" if available
                if not color_value_id:
                    for value in available_colors:
                        value_name = value.get("name", "")
                        if (
                            "multi" in value_name.lower()
                            or "multicolor" in value_name.lower()
                        ):
                            color_value_id = value.get("value_id")
                            color_value = value_name
                            logger.info(f"  Using default color: {value_name}")
                            break

                # Only add if we have a valid color
                if color_value:
                    property_values.append(
                        {
                            "property_id": color_prop.get("property_id"),
                            "property_name": color_prop.get("name"),
                            "value_ids": [color_value_id] if color_value_id else [],
                            "values": [color_value],
                            "scale_id": color_prop.get("scale_id"),
                        }
                    )

            # Add secondary color
            if "secondary_color" in property_map and "secondary_color" in attributes:
                color_prop = property_map["secondary_color"]
                color_value = attributes["secondary_color"]
                color_value_id = None

                # Get all available color values
                available_colors = color_prop.get("possible_values", [])
                logger.info(f"Available secondary colors: {len(available_colors)}")
                logger.info(f"Looking for secondary color match for: {color_value}")

                # First try exact match
                for value in available_colors:
                    value_name = value.get("name", "")
                    if color_value.lower() == value_name.lower():
                        color_value_id = value.get("value_id")
                        color_value = value_name
                        logger.info(
                            f"  Found exact secondary color match: {value_name}"
                        )
                        break

                # If no exact match, try partial match
                if not color_value_id:
                    for value in available_colors:
                        value_name = value.get("name", "")
                        if (
                            color_value.lower() in value_name.lower()
                            or value_name.lower() in color_value.lower()
                        ):
                            color_value_id = value.get("value_id")
                            color_value = value_name
                            logger.info(
                                f"  Found partial secondary color match: {value_name}"
                            )
                            break

                # Only add if we have a valid color
                if color_value and color_value_id:
                    property_values.append(
                        {
                            "property_id": color_prop.get("property_id"),
                            "property_name": color_prop.get("name"),
                            "value_ids": [color_value_id],
                            "values": [color_value],
                            "scale_id": color_prop.get("scale_id"),
                        }
                    )

            # Add dimensions (length and width)
            for dim in ["length", "width"]:
                if dim in property_map and dim in attributes:
                    dim_prop = property_map[dim]
                    dim_value = str(attributes[dim])
                    dim_unit = attributes.get(f"{dim}_unit", "inches")

                    # Log dimension information
                    logger.info(f"Setting {dim}: {dim_value} {dim_unit}")

                    # Check if this property has a scale (for units)
                    scale_id = dim_prop.get("scale_id")
                    if scale_id:
                        logger.info(f"  Property has scale_id: {scale_id}")

                    # Format the dimension value with the unit if needed
                    formatted_value = dim_value
                    if dim_unit and not scale_id:
                        formatted_value = f"{dim_value} {dim_unit}"

                    property_values.append(
                        {
                            "property_id": dim_prop.get("property_id"),
                            "property_name": dim_prop.get("name"),
                            "value_ids": [],
                            "values": [formatted_value],
                            "scale_id": scale_id,
                        }
                    )

            # Add occasion
            if "occasion" in property_map and "occasion" in attributes:
                occasion_prop = property_map["occasion"]
                occasion_value = attributes["occasion"]
                occasion_value_id = None

                # Try to match occasion to available values
                for value in occasion_prop.get("possible_values", []):
                    if occasion_value.lower() in value.get("name", "").lower():
                        occasion_value_id = value.get("value_id")
                        occasion_value = value.get("name")
                        break

                property_values.append(
                    {
                        "property_id": occasion_prop.get("property_id"),
                        "property_name": occasion_prop.get("name"),
                        "value_ids": [occasion_value_id] if occasion_value_id else [],
                        "values": [occasion_value],
                        "scale_id": occasion_prop.get("scale_id"),
                    }
                )

            # Add holiday
            if "holiday" in property_map and "holiday" in attributes:
                holiday_prop = property_map["holiday"]
                holiday_value = attributes["holiday"]
                holiday_value_id = None

                # Try to match holiday to available values
                for value in holiday_prop.get("possible_values", []):
                    if holiday_value.lower() in value.get("name", "").lower():
                        holiday_value_id = value.get("value_id")
                        holiday_value = value.get("name")
                        break

                property_values.append(
                    {
                        "property_id": holiday_prop.get("property_id"),
                        "property_name": holiday_prop.get("name"),
                        "value_ids": [holiday_value_id] if holiday_value_id else [],
                        "values": [holiday_value],
                        "scale_id": holiday_prop.get("scale_id"),
                    }
                )

            # Add subject
            if "subject" in property_map and "subjects" in attributes:
                subject_prop = property_map["subject"]
                subject_values = []
                subject_value_ids = []

                # Get all available subject values
                available_subjects = subject_prop.get("possible_values", [])
                logger.info(f"Available subjects: {len(available_subjects)}")

                # Try to match subjects to available values
                for subject in attributes["subjects"]:
                    found = False
                    best_match = None
                    best_match_id = None

                    # Log what we're looking for
                    logger.info(f"Looking for subject match for: {subject}")

                    # First try exact match
                    for value in available_subjects:
                        value_name = value.get("name", "")
                        if subject.lower() == value_name.lower():
                            subject_value_ids.append(value.get("value_id"))
                            subject_values.append(value_name)
                            found = True
                            logger.info(f"  Found exact subject match: {value_name}")
                            break

                    # If no exact match, try partial match
                    if not found:
                        for value in available_subjects:
                            value_name = value.get("name", "")
                            if (
                                subject.lower() in value_name.lower()
                                or value_name.lower() in subject.lower()
                            ):
                                best_match = value_name
                                best_match_id = value.get("value_id")
                                logger.info(
                                    f"  Found partial subject match: {value_name}"
                                )
                                break

                        if best_match:
                            subject_value_ids.append(best_match_id)
                            subject_values.append(best_match)
                            found = True

                    # If still no match, skip this subject
                    if not found:
                        logger.warning(f"  No match found for subject: {subject}")

                if subject_values:
                    property_values.append(
                        {
                            "property_id": subject_prop.get("property_id"),
                            "property_name": subject_prop.get("name"),
                            "value_ids": subject_value_ids,
                            "values": subject_values,
                            "scale_id": subject_prop.get("scale_id"),
                        }
                    )

            # Update the listing properties directly via inventory endpoint
            if property_values:
                logger.info(
                    f"Attempting to update {len(property_values)} properties for listing {listing_id} via inventory endpoint"
                )

                # Get the current listing inventory to preserve existing products
                current_inventory = self.get_listing_inventory(listing_id)
                if current_inventory and "products" in current_inventory:
                    # Use existing products if available
                    logger.info(
                        f"Found {len(current_inventory['products'])} existing products in inventory"
                    )

                    # Create a new product with our properties
                    # Make sure all property values have property_name
                    for prop_value in property_values:
                        if (
                            "property_name" not in prop_value
                            or not prop_value["property_name"]
                        ):
                            # Get the property name from the property map
                            for _, prop in property_map.items():
                                if prop.get("property_id") == prop_value["property_id"]:
                                    prop_value["property_name"] = prop.get("name")
                                    break

                    products = [
                        {
                            "sku": f"product-{listing_id}",
                            "property_values": property_values,
                            "offerings": [
                                {"quantity": 999, "is_enabled": True, "price": 3.32}
                            ],
                        }
                    ]

                    # Log the property values for debugging
                    logger.info(f"Property values: {property_values}")

                    # Try to update inventory with these properties
                    inventory_result = self.update_listing_inventory(
                        listing_id=listing_id, products=products
                    )

                    if inventory_result:
                        logger.info(
                            "Successfully set attributes using inventory endpoint"
                        )
                        return True
                    else:
                        logger.warning(
                            "Failed to set attributes using inventory endpoint"
                        )
                        return False
                else:
                    # If we couldn't get current inventory, create a new product
                    logger.info("No existing inventory found, creating new product")

                    # Create a simple product with the properties
                    # Make sure all property values have property_name
                    for prop_value in property_values:
                        if (
                            "property_name" not in prop_value
                            or not prop_value["property_name"]
                        ):
                            # Get the property name from the property map
                            for _, prop in property_map.items():
                                if prop.get("property_id") == prop_value["property_id"]:
                                    prop_value["property_name"] = prop.get("name")
                                    break

                    products = [
                        {
                            "sku": f"product-{listing_id}",
                            "property_values": property_values,
                            "offerings": [
                                {"quantity": 999, "is_enabled": True, "price": 3.32}
                            ],
                        }
                    ]

                    # Log the property values for debugging
                    logger.info(f"Property values: {property_values}")

                    # Try to update inventory with these properties
                    inventory_result = self.update_listing_inventory(
                        listing_id=listing_id, products=products
                    )

                    if inventory_result:
                        logger.info(
                            "Successfully set attributes using inventory endpoint"
                        )
                        return True
                    else:
                        logger.warning(
                            "Failed to set attributes using inventory endpoint"
                        )
                        return False
            else:
                logger.warning(f"No property values to update for listing {listing_id}")
                return True

        except Exception as e:
            logger.error(f"Error setting listing attributes: {e}")
            return False
