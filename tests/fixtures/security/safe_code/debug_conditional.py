# Safe code sample: Conditional Debug Mode
# These patterns should NOT trigger security warnings

import os

# Safe: Debug from environment variable
DEBUG = os.environ.get("DEBUG", "false").lower() == "true"

# Safe: Explicit production check
FLASK_DEBUG = os.getenv("FLASK_ENV") == "development"
FLASK_ENV = os.environ.get("FLASK_ENV", "production")

# Safe: Debug disabled by default
debug_mode = os.environ.get("APP_DEBUG", "0") == "1"

# Safe: Environment-based configuration
def is_debug_enabled():
    """Check debug mode from environment."""
    return os.environ.get("DEBUG_MODE", "false") == "true"


# Safe: Configuration class
class Settings:
    DEBUG = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")
    TESTING = os.getenv("TESTING", "false").lower() == "true"


# Safe: Explicit False
PRODUCTION_DEBUG = False
ENABLE_DEBUG = False

# Safe: Using settings module
from config import settings

app.run(debug=settings.DEBUG)  # Debug from config
