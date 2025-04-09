"""
Authentication module for Etsy API.
"""

import os
import json
import time
import requests
import secrets
import hashlib
import base64
from typing import Dict, Optional
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import urllib.parse

from utils.common import setup_logging

# Set up logging
logger = setup_logging(__name__)


# PKCE utilities
class PKCE:
    @staticmethod
    def generate_code_verifier(length=128):
        """Generate a code verifier for PKCE."""
        return secrets.token_urlsafe(length)

    @staticmethod
    def get_code_challenge(verifier):
        """Generate a code challenge from a verifier."""
        digest = hashlib.sha256(verifier.encode()).digest()
        return base64.urlsafe_b64encode(digest).decode().rstrip("=")


class CallbackHandler(BaseHTTPRequestHandler):
    """HTTP request handler for OAuth callback."""

    code = None

    def do_GET(self):
        """Handle GET request."""
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)

        if "code" in params:
            CallbackHandler.code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(
                b"<html><body><h1>Authentication successful!</h1><p>You can close this window now.</p></body></html>"
            )
        else:
            self.send_response(400)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(
                b"<html><body><h1>Authentication failed!</h1><p>No authorization code received.</p></body></html>"
            )

    def log_message(self, format_str, *args):
        """Suppress logging."""
        return


class EtsyAuth:
    """Handle authentication with Etsy API."""

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        redirect_uri: str = "http://localhost:3003/oauth/redirect",
        token_file: str = "etsy_token.json",
    ):
        """
        Initialize the Etsy authentication handler.

        Args:
            api_key: Etsy API key
            api_secret: Etsy API secret
            redirect_uri: Redirect URI for OAuth
            token_file: File to store the token
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.redirect_uri = redirect_uri
        self.token_file = token_file
        self.access_token = None
        self.refresh_token = None
        self.token_expiry = 0

        # PKCE parameters
        self.code_verifier = PKCE.generate_code_verifier(length=128)
        self.code_challenge = PKCE.get_code_challenge(self.code_verifier)
        self.state = secrets.token_hex(5)
        self.token_url = "https://api.etsy.com/v3/public/oauth/token"
        # Include listings_d scope for digital listings
        self.scope = " ".join(["listings_w", "listings_r", "listings_d", "email_r"])

        # Try to load existing token
        self._load_token()

    def _load_token(self) -> bool:
        """
        Load token from file.

        Returns:
            True if token was loaded successfully, False otherwise
        """
        try:
            if os.path.exists(self.token_file):
                with open(self.token_file, "r") as f:
                    token_data = json.load(f)
                    self.access_token = token_data.get("access_token")
                    self.refresh_token = token_data.get("refresh_token")
                    self.token_expiry = token_data.get("expiry", 0)

                    # Check if token is expired
                    if self.token_expiry < time.time():
                        logger.info("Token expired, refreshing...")
                        return self.refresh_access_token()

                    return True
            return False
        except Exception as e:
            logger.error(f"Error loading token: {e}")
            return False

    def _save_token(self) -> bool:
        """
        Save token to file.

        Returns:
            True if token was saved successfully, False otherwise
        """
        try:
            token_data = {
                "access_token": self.access_token,
                "refresh_token": self.refresh_token,
                "expiry": self.token_expiry,
            }

            with open(self.token_file, "w") as f:
                json.dump(token_data, f)

            return True
        except Exception as e:
            logger.error(f"Error saving token: {e}")
            return False

    def get_oauth_url(self) -> str:
        """
        Get the OAuth URL for user authorization.

        Returns:
            OAuth URL
        """
        params = {
            "response_type": "code",
            "client_id": self.api_key,
            "redirect_uri": self.redirect_uri,
            "scope": self.scope,
            "state": self.state,
            "code_challenge": self.code_challenge,
            "code_challenge_method": "S256",
        }

        # URL encode the parameters
        encoded_params = urllib.parse.urlencode(params)

        url = "https://www.etsy.com/oauth/connect?" + encoded_params
        return url

    def start_oauth_flow(self) -> bool:
        """
        Start the OAuth flow.

        Returns:
            True if authentication was successful, False otherwise
        """
        # Get the OAuth URL
        oauth_url = self.get_oauth_url()

        # Open the URL in the default browser
        webbrowser.open(oauth_url)

        # Start a local server to receive the callback
        server_address = ("", 3003)
        httpd = HTTPServer(server_address, CallbackHandler)

        # Start the server in a separate thread
        server_thread = threading.Thread(target=httpd.handle_request)
        server_thread.start()

        # Wait for the server to receive the callback
        server_thread.join(timeout=120)

        # Check if we received the code
        if CallbackHandler.code:
            # Exchange the code for an access token
            return self.exchange_code(CallbackHandler.code)
        else:
            logger.error("No authorization code received.")
            return False

    def exchange_code(self, code: str) -> bool:
        """
        Exchange the authorization code for an access token.

        Args:
            code: Authorization code

        Returns:
            True if exchange was successful, False otherwise
        """
        try:
            data = {
                "grant_type": "authorization_code",
                "client_id": self.api_key,
                "redirect_uri": self.redirect_uri,
                "code": code,
                "code_verifier": self.code_verifier,  # Use the code verifier generated during initialization
            }

            response = requests.post(self.token_url, data=data)

            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get("access_token")
                self.refresh_token = token_data.get("refresh_token")
                self.token_expiry = time.time() + token_data.get("expires_in", 3600)

                # Save the token
                self._save_token()

                logger.info("Successfully exchanged code for access token")
                return True
            else:
                logger.error(
                    f"Error exchanging code: {response.status_code} {response.text}"
                )
                return False
        except Exception as e:
            logger.error(f"Error exchanging code: {e}")
            return False

    def refresh_access_token(self) -> bool:
        """
        Refresh the access token.

        Returns:
            True if refresh was successful, False otherwise
        """
        if not self.refresh_token:
            logger.error("No refresh token available.")
            return False

        try:
            data = {
                "grant_type": "refresh_token",
                "client_id": self.api_key,
                "refresh_token": self.refresh_token,
            }

            response = requests.post(self.token_url, data=data)

            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get("access_token")
                self.refresh_token = token_data.get("refresh_token")
                self.token_expiry = time.time() + token_data.get("expires_in", 3600)

                # Save the token
                self._save_token()

                logger.info("Successfully refreshed access token")
                return True
            else:
                logger.error(
                    f"Error refreshing token: {response.status_code} {response.text}"
                )
                return False
        except Exception as e:
            logger.error(f"Error refreshing token: {e}")
            return False

    def get_headers(self) -> Dict[str, str]:
        """
        Get the headers for API requests.

        Returns:
            Headers for API requests
        """
        if not self.access_token:
            logger.error("No access token available.")
            return {}

        # Check if token is expired
        if self.token_expiry < time.time():
            logger.info("Token expired, refreshing...")
            if not self.refresh_access_token():
                logger.error("Failed to refresh token.")
                return {}

        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
        }

    def is_authenticated(self) -> bool:
        """
        Check if the user is authenticated.

        Returns:
            True if authenticated, False otherwise
        """
        return self.access_token is not None and self.token_expiry > time.time()
