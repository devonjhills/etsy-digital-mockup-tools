"""Environment variable loading utilities."""

import os
import sys
from pathlib import Path
from typing import Optional, Dict

# Import dotenv if available
try:
    import dotenv
    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False

def find_env_file() -> Optional[Path]:
    """Find the .env file in the project root."""
    # Start from current directory and work up
    current = Path.cwd()
    
    # Also check the directory where this script is located
    script_dir = Path(__file__).parent.parent
    
    for base_dir in [current, script_dir]:
        for path in [base_dir, *base_dir.parents]:
            env_file = path / ".env"
            if env_file.exists():
                return env_file
            
            # Also check for .env.local
            env_local = path / ".env.local"
            if env_local.exists():
                return env_local
    
    return None


def load_environment(env_file: Optional[str] = None) -> bool:
    """Load environment variables from .env file.
    
    Args:
        env_file: Optional path to specific .env file
        
    Returns:
        True if environment file was loaded successfully
    """
    if HAS_DOTENV:
        try:
            if env_file:
                env_path = Path(env_file)
            else:
                env_path = find_env_file()
            
            if env_path and env_path.exists():
                dotenv.load_dotenv(env_path)
                return True
        except Exception:
            pass
    
    # Fallback to manual loading
    return load_env_from_file(env_file or ".env")


def load_env_from_file(env_file: str = ".env") -> bool:
    """Load environment variables from a .env file manually.
    
    Args:
        env_file: Path to the .env file
        
    Returns:
        True if file was loaded successfully
    """
    if not os.path.exists(env_file):
        return False
    
    try:
        import re
        with open(env_file, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                    
                # Handle export VAR=value format
                if line.startswith("export "):
                    line = line[7:]  # Remove "export " prefix
                    
                # Parse VAR=value format
                match = re.match(r"^([A-Za-z0-9_]+)=[\"']?(.*?)[\"']?$", line)
                if match:
                    key, value = match.groups()
                    os.environ[key] = value
        return True
    except Exception:
        return False


def get_required_env_vars() -> list[str]:
    """Get list of required environment variables."""
    return [
        "ETSY_API_KEY",
        "ETSY_API_SECRET", 
        "ETSY_SHOP_ID"
    ]


def get_optional_env_vars() -> list[str]:
    """Get list of optional environment variables."""
    return [
        "GEMINI_API_KEY",
        "OPENAI_API_KEY",
        "GEMINI_MODEL"
    ]


def validate_environment() -> tuple[bool, list[str]]:
    """Validate that required environment variables are set.
    
    Returns:
        Tuple of (is_valid, list_of_missing_vars)
    """
    missing_vars = []
    
    for var in get_required_env_vars():
        if not os.getenv(var):
            missing_vars.append(var)
    
    return len(missing_vars) == 0, missing_vars


def get_env_var(var_name: str, default: Optional[str] = None) -> Optional[str]:
    """Get environment variable value.
    
    Args:
        var_name: Name of the environment variable
        default: Default value if variable is not set
        
    Returns:
        Value of the environment variable or default
    """
    return os.getenv(var_name, default)


def setup_environment() -> bool:
    """Setup environment by loading .env and validating required vars.
    
    Returns:
        True if environment is properly configured
    """
    # Load environment file
    load_environment()
    
    # Validate required variables
    is_valid, missing_vars = validate_environment()
    
    if not is_valid:
        print(f"Missing required environment variables: {', '.join(missing_vars)}")
        print("Please create a .env file with the required variables.")
        return False
    
    return True
