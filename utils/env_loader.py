"""
Utility module for loading environment variables from .env file.
"""
import os
import re
from typing import Dict

def load_env_from_file(env_file: str = ".env") -> Dict[str, str]:
    """
    Load environment variables from a .env file.
    
    Args:
        env_file: Path to the .env file
        
    Returns:
        Dictionary of environment variables
    """
    env_vars = {}
    
    if not os.path.exists(env_file):
        return env_vars
    
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
                env_vars[key] = value
                os.environ[key] = value
    
    return env_vars
