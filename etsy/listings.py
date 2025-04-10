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
        # Use the hardcoded shop ID for digitalveil
        return "42865309"

        # Uncomment this code if you want to fetch the shop ID dynamically
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
