# Safe code sample: Secrets from Environment Variables
# These patterns should NOT trigger security warnings

import os
from pathlib import Path

# Safe: Reading from environment variables
API_KEY = os.environ.get("API_KEY")
SECRET_KEY = os.getenv("SECRET_KEY", "")
PASSWORD = os.environ["DB_PASSWORD"]

# Safe: Using environment with defaults
AWS_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY_ID")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# Safe: Configuration from environment
config = {
    "api_key": os.environ.get("API_KEY"),
    "secret": os.getenv("SECRET_TOKEN"),
}


def get_credentials():
    """Safe: Get credentials from environment."""
    return {
        "username": os.environ.get("APP_USERNAME"),
        "password": os.environ.get("APP_PASSWORD"),
    }


# Safe: Loading from secure file
def load_secrets_from_file():
    """Load secrets from a secure secrets file."""
    secrets_path = Path("/run/secrets/api_key")
    if secrets_path.exists():
        return secrets_path.read_text().strip()
    return None
