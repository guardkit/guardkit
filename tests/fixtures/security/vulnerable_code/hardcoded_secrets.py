# Vulnerable code sample: Hardcoded secrets
# These patterns should be detected by SecurityChecker

# Critical: Hardcoded API keys
API_KEY = "sk-1234567890abcdef1234567890abcdef"
SECRET_KEY = "my-super-secret-key-that-should-not-be-here"
PASSWORD = "admin123"

# Different variations
AWS_ACCESS_KEY = "AKIAIOSFODNN7EXAMPLE"
DB_PASSWORD = "production-db-password"

# In dictionary form
config = {
    "api_key": "sk-abcdef123456",
    "secret": "another-hardcoded-secret",
}


def get_credentials():
    """Return hardcoded credentials - very bad practice."""
    return {
        "username": "admin",
        "password": "supersecretpassword",  # Hardcoded!
    }
