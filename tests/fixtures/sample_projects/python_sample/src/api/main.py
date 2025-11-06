from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class User(BaseModel):
    id: int
    name: str
    email: str

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/users/{user_id}", response_model=User)
def get_user(user_id: int):
    return User(id=user_id, name="John Doe", email="john@example.com")
