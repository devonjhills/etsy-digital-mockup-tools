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

from src.utils.common import setup_logging

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
        logger.info(f"Received callback: {self.path}")

        # Handle both root path and /oauth/redirect path
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query = parsed_url.query
        params = urllib.parse.parse_qs(query)

        logger.info(f"Path: {path}, Query parameters: {params}")

        # Check if this is the Etsy redirect with a code
        if "code" in params:
            CallbackHandler.code = params["code"][0]
            logger.info(f"Received authorization code: {CallbackHandler.code[:5]}...")
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(
                b"<html><body><h1>Authentication successful!</h1><p>You can close this window now.</p></body></html>"
            )
        # If it's the redirect path but no code, show an error
        elif path == "/oauth/redirect":
            logger.error(f"Redirect received but no code in parameters: {params}")
            self.send_response(400)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(
                b"<html><body><h1>Authentication failed!</h1><p>No authorization code received.</p></body></html>"
            )
        # For root path or other paths, show a waiting message
        else:
            logger.info("Received request to root path, showing waiting message")
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(
                b"<html><body><h1>Waiting for Etsy authentication...</h1><p>Please complete the authentication in the Etsy window.</p></body></html>"
            )

    def log_message(self, format_str, *args):
        """Log messages to our logger instead of stderr."""
        logger.debug(f"HTTP Server: {format_str % args}")


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

            # Get absolute path for token file
            token_path = os.path.abspath(self.token_file)
            logger.info(f"Saving token to: {token_path}")

            # Ensure directory exists
            token_dir = os.path.dirname(token_path)
            if token_dir and not os.path.exists(token_dir):
                os.makedirs(token_dir)
                logger.info(f"Created directory: {token_dir}")

            with open(token_path, "w") as f:
                json.dump(token_data, f)
                logger.info(f"Token saved successfully")

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
        # Reset the callback handler code
        CallbackHandler.code = None

        # Get the OAuth URL
        oauth_url = self.get_oauth_url()
        logger.info(f"Opening OAuth URL: {oauth_url}")

        # Create a server that will keep running until we get the code
        server_address = ("", 3003)
        try:
            # Create a custom server class that we can stop from another thread
            class StoppableHTTPServer(HTTPServer):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, **kwargs)
                    self.stop_requested = False

                def serve_until_code_received(self, timeout=120):
                    """Serve requests until code is received or timeout is reached."""
                    start_time = time.time()
                    while (
                        not self.stop_requested and time.time() - start_time < timeout
                    ):
                        self.handle_request()
                        if CallbackHandler.code:
                            logger.info("Code received, stopping server")
                            self.stop_requested = True
                            return True
                    return False

            # Create and start the server
            httpd = StoppableHTTPServer(server_address, CallbackHandler)
            logger.info(f"Started HTTP server on port 3003")

            # Open the URL in the default browser
            webbrowser.open(oauth_url)
            logger.info("Opened browser for authentication")

            # Wait for the code in a separate thread so we can handle keyboard interrupts
            def serve_in_thread():
                return httpd.serve_until_code_received(timeout=120)

            server_thread = threading.Thread(target=serve_in_thread)
            server_thread.daemon = (
                True  # Allow the program to exit even if thread is running
            )
            server_thread.start()

            # Wait for the server thread to complete
            server_thread.join(timeout=120)

            # Check if we received the code
            if CallbackHandler.code:
                logger.info("Received authorization code, exchanging for token...")
                # Exchange the code for an access token
                return self.exchange_code(CallbackHandler.code)
            else:
                logger.error("No authorization code received after timeout.")
                return False
        except Exception as e:
            logger.error(f"Error in OAuth flow: {e}")
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
            "x-api-key": f"{self.api_key}:{self.api_secret}",
        }

    def is_authenticated(self) -> bool:
        """
        Check if the user is authenticated.

        Returns:
            True if authenticated, False otherwise
        """
        return self.access_token is not None and self.token_expiry > time.time()
