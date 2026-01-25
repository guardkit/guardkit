# Vulnerable code sample: CORS Wildcard
# These patterns should be detected by SecurityChecker

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Vulnerable: CORS wildcard allows any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow any origin - security risk!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Alternative vulnerable pattern
cors_config = {
    "origins": ["*"],
    "allow_credentials": True,
}

# In Flask
from flask_cors import CORS

flask_app = Flask(__name__)
CORS(flask_app, origins=["*"])  # Vulnerable!
