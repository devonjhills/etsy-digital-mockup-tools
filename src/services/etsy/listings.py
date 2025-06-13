"""
Etsy listings module for creating and managing Etsy listings.
"""

import os
import requests
from typing import Dict, List, Optional, Any

from src.utils.common import setup_logging
from src.services.etsy.auth import EtsyAuth

# Set up logging
logger = setup_logging(__name__)


class EtsyListings:
    """Class for managing Etsy listings."""

    def __init__(self, auth: EtsyAuth):
        """
        Initialize the EtsyListings class.

        Args:
            auth: EtsyAuth instance
        """
        self.auth = auth
        self.base_url = "https://openapi.etsy.com/v3"
        self.shop_id = os.environ.get("ETSY_SHOP_ID")

        # If shop ID is not in environment, try to get it from the API
        if not self.shop_id:
            self.shop_id = self._get_shop_id()
            if self.shop_id:
                logger.info(f"Retrieved shop ID from API: {self.shop_id}")
        else:
            logger.info(f"Using shop ID from environment: {self.shop_id}")
            
        if not self.shop_id:
            logger.error("No shop ID available - cannot proceed with Etsy operations")

    def _get_shop_id(self) -> Optional[str]:
        """
        Get the shop ID for the authenticated user.

        Returns:
            Shop ID or None if not found
        """
        if not self.auth.is_authenticated():
            logger.error("Not authenticated with Etsy.")
            return None

        try:
            url = f"{self.base_url}/application/users/me/shops"
            headers = self.auth.get_headers()
            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                shops = response.json().get("results", [])
                if shops:
                    shop_id = shops[0].get("shop_id")
                    # Save to environment for future use
                    os.environ["ETSY_SHOP_ID"] = str(shop_id)
                    return str(shop_id)
                else:
                    logger.error("No shops found for authenticated user.")
                    return None
            else:
                logger.error(
                    f"Error getting shop ID: {response.status_code} {response.text}"
                )
                return None
        except Exception as e:
            logger.error(f"Error getting shop ID: {e}")
            return None

    def get_shipping_profiles(self) -> Optional[List[Dict]]:
        """
        Get shipping profiles for the shop.

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
                return response.json().get("results", [])
            else:
                logger.error(
                    f"Error getting shipping profiles: {response.status_code} {response.text}"
                )
                return None
        except Exception as e:
            logger.error(f"Error getting shipping profiles: {e}")
            return None

    def create_listing(
        self,
        title: str,
        description: str,
        price: float,
        quantity: int,
        tags: List[str],
        taxonomy_id: int,
        who_made: str = "i_did",
        is_supply: bool = False,
        when_made: str = "2020_2025",
        is_digital: bool = True,
        is_personalizable: bool = False,
        personalization_instructions: str = "",
        is_draft: bool = False,
        shipping_profile_id: Optional[int] = None,
        shop_section_id: Optional[int] = None,
        materials: Optional[List[str]] = None,
    ) -> Optional[Dict]:
        """
        Create a new Etsy listing.

        Args:
            title: Listing title
            description: Listing description
            price: Listing price
            quantity: Listing quantity
            tags: List of tags
            taxonomy_id: Taxonomy ID
            who_made: Who made the item
            is_supply: Whether the item is a supply
            when_made: When the item was made
            is_digital: Whether the item is digital
            is_personalizable: Whether the item is personalizable
            personalization_instructions: Personalization instructions
            is_draft: Whether the listing is a draft
            shipping_profile_id: Shipping profile ID
            shop_section_id: Shop section ID
            materials: List of materials

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
                "title": title,
                "description": description,
                "price": price,
                "quantity": quantity,
                "tags": tags,
                "taxonomy_id": taxonomy_id,
                "who_made": who_made,
                "is_supply": is_supply,
                "when_made": when_made,
                "is_digital": is_digital,
                "is_personalizable": is_personalizable,
                "personalization_is_required": False,
                "state": "draft" if is_draft else "active",
            }

            # Add optional fields if provided
            if personalization_instructions:
                data["personalization_instructions"] = personalization_instructions

            if shipping_profile_id:
                data["shipping_profile_id"] = shipping_profile_id

            if shop_section_id:
                data["shop_section_id"] = shop_section_id

            if materials:
                data["materials"] = materials

            # For digital listings, add type
            if is_digital:
                data["type"] = "download"

            # Make the request
            response = requests.post(url, headers=headers, json=data)

            # Check if the request was successful
            if response.status_code == 201:
                return response.json()
            else:
                logger.error(
                    f"Error creating listing: {response.status_code} {response.text}"
                )
                return None
        except Exception as e:
            logger.error(f"Error creating listing: {e}")
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
                return response.json()
            else:
                logger.error(
                    f"Error getting listing: {response.status_code} {response.text}"
                )
                return None
        except Exception as e:
            logger.error(f"Error getting listing: {e}")
            return None

    def get_shop_sections(self) -> Optional[List[Dict]]:
        """
        Get all shop sections for the shop.

        Returns:
            List of shop sections or None if not found
        """
        if not self.shop_id:
            logger.error("No shop ID available.")
            return None

        try:
            url = f"{self.base_url}/application/shops/{self.shop_id}/sections"
            headers = self.auth.get_headers()
            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                return response.json().get("results", [])
            else:
                logger.error(
                    f"Error getting shop sections: {response.status_code} {response.text}"
                )
                return None
        except Exception as e:
            logger.error(f"Error getting shop sections: {e}")
            return None

    def upload_listing_image(
        self, listing_id: int, image_path: str, rank: int = 1
    ) -> Optional[Dict]:
        """
        Upload an image to a listing.

        Args:
            listing_id: Listing ID
            image_path: Path to the image file
            rank: Image rank (1 is the main image)

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

            # Remove Content-Type from headers to let requests set it correctly for multipart/form-data
            if "Content-Type" in headers:
                del headers["Content-Type"]

            with open(image_path, "rb") as f:
                files = {"image": (os.path.basename(image_path), f, "image/jpeg")}
                data = {
                    "rank": str(rank)
                }  # Convert to string to ensure proper form encoding
                response = requests.post(url, headers=headers, files=files, data=data)

            # Check if the request was successful
            if response.status_code == 201:
                return response.json()
            else:
                logger.error(
                    f"Error uploading image: {response.status_code} {response.text}"
                )
                return None
        except Exception as e:
            logger.error(f"Error uploading image: {e}")
            return None

    def upload_digital_file(
        self, listing_id: int, file_path: str, rank: int = 1
    ) -> Optional[Dict]:
        """
        Upload a digital file to a listing.

        Args:
            listing_id: Listing ID
            file_path: Path to the file
            rank: File rank

        Returns:
            File data or None if upload failed
        """
        if not self.shop_id:
            logger.error("No shop ID available.")
            return None

        try:
            url = f"{self.base_url}/application/shops/{self.shop_id}/listings/{listing_id}/files"

            # Remove Content-Type header for file upload
            upload_headers = self.auth.get_headers()
            if "Content-Type" in upload_headers:
                del upload_headers["Content-Type"]

            with open(file_path, "rb") as f:
                files = {"file": (os.path.basename(file_path), f, "application/zip")}
                data = {"name": os.path.basename(file_path), "rank": rank}
                
                response = requests.post(url, headers=upload_headers, files=files, data=data)

                if response.status_code == 201:
                    file_data = response.json()
                    file_id = file_data.get('listing_file_id')
                    logger.info(f"✓ Digital file uploaded successfully: {os.path.basename(file_path)} (ID: {file_id})")
                    logger.info(f"Upload response: {file_data}")
                    return file_data
                else:
                    logger.error(
                        f"✗ Error uploading digital file: {response.status_code} {response.text}"
                    )
                    return None
        except Exception as e:
            logger.error(f"Exception uploading digital file {file_path}: {e}")
            return None

    def upload_video(
        self, listing_id: int, video_path: str, rank: int = 1
    ) -> Optional[Dict]:
        """
        Upload a video to a listing.

        Args:
            listing_id: Listing ID
            video_path: Path to the video file
            rank: Video rank (not used by Etsy API but kept for consistency)

        Returns:
            Video data or None if upload failed
        """
        if not self.shop_id:
            logger.error("No shop ID available.")
            return None

        # Validate video file before upload
        from src.utils.video_utils import validate_video_for_etsy
        is_valid, validation_message = validate_video_for_etsy(video_path)
        if not is_valid:
            logger.error(f"Video validation failed: {validation_message}")
            return None
        
        logger.info(f"Video validation passed: {validation_message}")

        try:
            # Log video file details
            file_size = os.path.getsize(video_path)
            logger.info(f"Uploading video: {video_path} ({file_size / (1024*1024):.1f}MB)")
            
            url = f"{self.base_url}/application/shops/{self.shop_id}/listings/{listing_id}/videos"
            headers = self.auth.get_headers()

            # Remove Content-Type from headers to let requests set it correctly for multipart/form-data
            if "Content-Type" in headers:
                del headers["Content-Type"]

            with open(video_path, "rb") as f:
                files = {"video": (os.path.basename(video_path), f, "video/mp4")}
                data = {"name": os.path.basename(video_path)}
                response = requests.post(url, headers=headers, files=files, data=data)

            # Check if the request was successful
            if response.status_code == 201:
                logger.info(f"Video uploaded successfully to listing {listing_id}")
                return response.json()
            else:
                logger.error(f"Video upload failed for {video_path}")
                logger.error(f"HTTP Status: {response.status_code}")
                logger.error(f"Response: {response.text}")
                logger.error(f"Video details - Size: {file_size / (1024*1024):.1f}MB, Path: {video_path}")
                return None
        except Exception as e:
            logger.error(f"Exception during video upload: {e}")
            logger.error(f"Video file: {video_path}")
            return None

    def get_properties_by_taxonomy_id(self, taxonomy_id: int) -> Optional[List[Dict]]:
        """
        Get properties for a taxonomy ID.

        Args:
            taxonomy_id: Taxonomy ID

        Returns:
            List of properties or None if not found
        """
        try:
            url = f"{self.base_url}/application/seller-taxonomy/nodes/{taxonomy_id}/properties"
            headers = self.auth.get_headers()
            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                return response.json().get("results", [])
            else:
                logger.error(
                    f"Error getting properties: {response.status_code} {response.text}"
                )
                return None
        except Exception as e:
            logger.error(f"Error getting properties: {e}")
            return None

    def update_listing_inventory(
        self, listing_id: int, products: List[Dict]
    ) -> Optional[Dict]:
        """
        Update the inventory for a listing.

        Args:
            listing_id: Listing ID
            products: List of products with properties and offerings

        Returns:
            Inventory data or None if update failed
        """
        if not self.shop_id:
            logger.error("No shop ID available.")
            return None

        try:
            url = f"{self.base_url}/application/listings/{listing_id}/inventory"
            headers = self.auth.get_headers()

            # Prepare the data
            data = {"products": products}

            # Make the request
            response = requests.put(url, headers=headers, json=data)

            # Check if the request was successful
            if response.status_code == 200:
                logger.info(f"Listing inventory updated for listing: {listing_id}")
                return response.json()
            else:
                logger.error(
                    f"Error updating listing inventory: {response.status_code} {response.text}"
                )
                return None
        except Exception as e:
            logger.error(f"Error updating listing inventory: {e}")
            return None

    def get_listing_files(self, listing_id: int) -> Optional[List[Dict]]:
        """
        Get all digital files for a listing to verify they were uploaded successfully.

        Args:
            listing_id: Listing ID

        Returns:
            List of file data or None if retrieval failed
        """
        if not self.shop_id:
            logger.error("No shop ID available.")
            return None

        try:
            url = f"{self.base_url}/application/shops/{self.shop_id}/listings/{listing_id}/files"
            headers = self.auth.get_headers()
            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                files_data = response.json().get("results", [])
                logger.info(f"Found {len(files_data)} digital files for listing {listing_id}")
                for file_data in files_data:
                    file_id = file_data.get('listing_file_id')
                    filename = file_data.get('filename', 'Unknown')
                    file_size = file_data.get('filesize', 0)
                    logger.info(f"  - File ID: {file_id}, Name: {filename}, Size: {file_size} bytes")
                return files_data
            else:
                logger.error(
                    f"Error getting listing files: {response.status_code} {response.text}"
                )
                return None
        except Exception as e:
            logger.error(f"Error getting listing files: {e}")
            return None

    def verify_digital_files(self, listing_id: int, expected_filenames: Optional[List[str]] = None) -> bool:
        """
        Verify that digital files were uploaded successfully to a listing.

        Args:
            listing_id: Listing ID
            expected_filenames: Optional list of expected filenames to check for

        Returns:
            True if verification successful, False otherwise
        """
        # First check the listing state
        listing_info = self.get_listing(listing_id)
        if listing_info:
            listing_state = listing_info.get('state', 'unknown')
            logger.info(f"Listing {listing_id} state: {listing_state}")
        
        files = self.get_listing_files(listing_id)
        
        if files is None:
            logger.error(f"Failed to retrieve files for listing {listing_id}")
            return False
        
        if len(files) == 0:
            logger.error(f"No digital files found for listing {listing_id}")
            return False
        
        # Log detailed file information for debugging
        total_size = 0
        for file_data in files:
            file_size_mb = file_data.get('size_bytes', 0) / (1024 * 1024) if file_data.get('size_bytes') else 0
            total_size += file_size_mb
            create_time = file_data.get('create_timestamp', 0)
            logger.info(f"  File details: {file_data.get('filename')} - {file_size_mb:.1f}MB - Created: {create_time}")
        
        logger.info(f"Total files size: {total_size:.1f}MB")
        
        # If expected filenames provided, verify they exist
        if expected_filenames:
            found_filenames = [f.get('filename', '') for f in files]
            missing_files = []
            for expected_name in expected_filenames:
                if not any(expected_name in found_name for found_name in found_filenames):
                    missing_files.append(expected_name)
            
            if missing_files:
                logger.error(f"Missing expected files in listing {listing_id}: {missing_files}")
                return False
            else:
                logger.info(f"✓ All expected files verified for listing {listing_id}")
        else:
            logger.info(f"✓ Digital files verified for listing {listing_id} ({len(files)} files found)")
        
        return True
