# Safe code sample: Explicit CORS Configuration
# These patterns should NOT trigger security warnings

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Safe: Explicit allowed origins
ALLOWED_ORIGINS = [
    "https://example.com",
    "https://api.example.com",
    "https://admin.example.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # Explicit origins, no wildcard
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)

# Safe: Environment-based configuration
import os

cors_origins = os.environ.get("CORS_ORIGINS", "").split(",")

# Safe: Origin validation
def validate_origin(origin: str) -> bool:
    """Validate origin against whitelist."""
    allowed = {"https://example.com", "https://api.example.com"}
    return origin in allowed


# Safe: Flask with explicit origins
from flask import Flask
from flask_cors import CORS

flask_app = Flask(__name__)
CORS(flask_app, origins=["https://example.com", "https://app.example.com"])
