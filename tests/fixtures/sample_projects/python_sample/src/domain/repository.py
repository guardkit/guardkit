from abc import ABC, abstractmethod
from typing import List, Optional
from .models import User

class UserRepository(ABC):
    """Repository pattern for user data access."""
    
    @abstractmethod
    def get_by_id(self, user_id: int) -> Optional[User]:
        pass
    
    @abstractmethod
    def list_all(self) -> List[User]:
        pass
    
    @abstractmethod
    def create(self, user: User) -> User:
        pass
