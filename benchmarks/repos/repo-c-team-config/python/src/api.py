"""Team project API module."""

from typing import Dict, List, Optional
import json
import hashlib


class UserManager:
    """Manage user accounts and permissions."""
    
    def __init__(self):
        self.users: Dict[str, Dict[str, str]] = {}
        self.sessions: Dict[str, str] = {}
    
    def create_user(self, username: str, email: str, password: str) -> bool:
        """Create a new user account."""
        if username in self.users:
            return False
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        self.users[username] = {
            "email": email,
            "password_hash": password_hash,
            "role": "user"
        }
        return True
    
    def authenticate(self, username: str, password: str) -> Optional[str]:
        """Authenticate user and return session token."""
        if username not in self.users:
            return None
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        if self.users[username]["password_hash"] != password_hash:
            return None
        
        session_token = hashlib.md5(f"{username}{password_hash}".encode()).hexdigest()
        self.sessions[session_token] = username
        return session_token
    
    def get_user_role(self, session_token: str) -> Optional[str]:
        """Get user role from session token."""
        if session_token not in self.sessions:
            return None
        
        username = self.sessions[session_token]
        return self.users[username]["role"]


class ProjectAPI:
    """Team project management API."""
    
    def __init__(self):
        self.projects: Dict[str, Dict] = {}
        self.user_manager = UserManager()
    
    def create_project(self, name: str, description: str, owner: str) -> bool:
        """Create a new project."""
        if name in self.projects:
            return False
        
        self.projects[name] = {
            "description": description,
            "owner": owner,
            "members": [owner],
            "tasks": [],
            "created_at": "2025-11-02T00:00:00Z"
        }
        return True
    
    def add_member(self, project_name: str, username: str) -> bool:
        """Add member to project."""
        if project_name not in self.projects:
            return False
        
        if username not in self.projects[project_name]["members"]:
            self.projects[project_name]["members"].append(username)
        return True
    
    def get_projects_for_user(self, username: str) -> List[Dict]:
        """Get all projects for a user."""
        user_projects = []
        for name, project in self.projects.items():
            if username in project["members"]:
                user_projects.append({
                    "name": name,
                    "description": project["description"],
                    "role": "owner" if project["owner"] == username else "member"
                })
        return user_projects


if __name__ == "__main__":
    api = ProjectAPI()
    
    # Create users
    api.user_manager.create_user("alice", "alice@example.com", "password123")
    api.user_manager.create_user("bob", "bob@example.com", "password456")
    
    # Create project
    api.create_project("Website Redesign", "Redesign company website", "alice")
    api.add_member("Website Redesign", "bob")
    
    # Get projects
    alice_projects = api.get_projects_for_user("alice")
    print(f"Alice's projects: {json.dumps(alice_projects, indent=2)}")