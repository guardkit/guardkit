# Vulnerable code sample: Debug Mode Enabled
# These patterns should be detected by SecurityChecker

# Django settings
DEBUG = True  # Never enable in production!

# Flask settings
FLASK_DEBUG = True
FLASK_ENV = "development"

# FastAPI
debug_mode = True

# Hardcoded debug flags
app.run(debug=True)  # Should use environment variable

# Configuration object
settings = {
    "DEBUG": True,
    "verbose": True,
}
