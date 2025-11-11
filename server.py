"""
server.py - FastAPI server for IntelliOS Firebase Database system
Provides endpoints for real-time database operations including login/signup and workspaces management
"""
import os
import logging
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import json
from firebase_admin import credentials, firestore

# Initialize Firebase
from firebase_admin import credentials, firestore, initialize_app, get_app, App

# Initialize Firebase safely (avoid re-initialization)
    
creds_dict = json.loads(os.environ["SERVICE_ACCOUNT_KEY_JSON"])
cred = credentials.Certificate(creds_dict)
app_ = initialize_app(cred)
db = firestore.client(app_)


# Set up the logger
logger = logging.getLogger(__name__)


# Initialize FastAPI app
app = FastAPI(
    title="IntelliOS Firestore API",
    description="API for IntelliOS Firestore database system",
    version="1.0.0",
)

# Add CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define response models


class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    status: str
    message: str
    workspaces: Optional[Dict[str, Dict[str, Any]]] = None

class SignupRequest(BaseModel):
    username: str
    password: str
    name: str
    email: str

class SignupResponse(BaseModel):
    status: str
    message: str

class CreateWorkspaceRequest(BaseModel):
    username: str
    workspace_name: str
    state: Dict[str, Any]

class CreateWorkspaceResponse(BaseModel):
    status: str
    message: str

class GetWorkspacesRequest(BaseModel):
    username: str

class GetWorkspacesResponse(BaseModel):
    status: str
    workspaces: Dict[str, Dict[str, Any]]

class DeleteWorkspaceRequest(BaseModel):
    username: str
    workspace_name: str

class DeleteWorkspaceResponse(BaseModel):
    status: str
    message: str

# Routes
@app.get("/", tags=["Root"])
async def read_root():
    """Root endpoint - health check"""
    return {"status": "online", "message": "IntelliOS API is running"}

@app.post("/api/login", response_model=LoginResponse, tags=["Authentication"])
async def login(request: LoginRequest):
    """
    Authenticate user login
    """
    try:
        # Get user document from Firestore
        doc = db.collection("DDNA").document(request.username).get()
        
        if not doc.exists:
            return LoginResponse(
                status="error",
                message="Username not found",
                workspaces=None
            )
            
        user_data = doc.to_dict()
        if user_data.get("password") != request.password:
            return LoginResponse(
                status="error",
                message="Incorrect Password",
                workspaces=None
            )
            
        # Return success with workspaces
        return LoginResponse(
            status="success",
            message="Successful",
            workspaces=user_data.get("workspaces", {})
        )
            
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Login failed: {str(e)}"
        )

@app.post("/api/signup", response_model=SignupResponse, tags=["Authentication"])
async def signup(request: SignupRequest):
    """
    Create new user account
    """
    try:
        # Check if username already exists
        doc = db.collection("DDNA").document(request.username).get()
        if doc.exists:
            return SignupResponse(
                status="error",
                message="Username already exists"
            )
            
        # Create new user document
        user_data = {
            "username": request.username,
            "password": request.password,
            "name": request.name,
            "email": request.email,
            "workspaces": {}
        }
        
        db.collection("DDNA").document(request.username).set(user_data)
        
        return SignupResponse(
            status="success",
            message="Account created successfully"
        )
            
    except Exception as e:
        logger.error(f"Signup error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Signup failed: {str(e)}"
        )

@app.post("/api/workspace", response_model=CreateWorkspaceResponse, tags=["Workspace Management"])
async def create_update_workspace(request: CreateWorkspaceRequest):
    """
    Create or update a workspace with the given name and state
    
    Args:
        request: CreateWorkspaceRequest containing username, workspace_name and state
        
    Returns:
        CreateWorkspaceResponse with status and message
    """
    try:
        # Get user document
        doc_ref = db.collection("DDNA").document(request.username)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
            
        # Get current workspaces
        user_data = doc.to_dict()
        workspaces = user_data.get("workspaces", {})
        
        # Add or update workspace
        workspaces[request.workspace_name] = request.state
        
        # Update Firestore document
        doc_ref.update({
            "workspaces": workspaces
        })
            
        return CreateWorkspaceResponse(
            status="success",
            message=f"Workspace '{request.workspace_name}' created/updated successfully"
        )
            
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error creating workspace: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error creating workspace: {str(e)}"
        )

@app.post("/api/workspaces", response_model=GetWorkspacesResponse, tags=["Workspace Management"])
async def get_all_workspaces(request: GetWorkspacesRequest):
    """
    Get all workspaces and their states for a user
    
    Args:
        request: GetWorkspacesRequest containing username
        
    Returns:
        GetWorkspacesResponse containing a dictionary of workspace names and their states
    """
    try:
        # Get user document
        doc = db.collection("DDNA").document(request.username).get()
        
        if not doc.exists:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
            
        user_data = doc.to_dict()
        workspaces = user_data.get("workspaces", {})
                    
        return GetWorkspacesResponse(
            status="success",
            workspaces=workspaces
        )
            
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error getting workspaces: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting workspaces: {str(e)}"
        )

@app.delete("/api/workspace", response_model=DeleteWorkspaceResponse, tags=["Workspace Management"])
async def delete_workspace(request: DeleteWorkspaceRequest):
    """
    Delete a workspace for a user
    
    Args:
        request: DeleteWorkspaceRequest containing username and workspace_name
        
    Returns:
        DeleteWorkspaceResponse with status and message
    """
    try:
        # Get user document
        doc_ref = db.collection("DDNA").document(request.username)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
            
        # Get current workspaces
        user_data = doc.to_dict()
        workspaces = user_data.get("workspaces", {})
        
        # Check if workspace exists
        if request.workspace_name not in workspaces:
            raise HTTPException(
                status_code=404,
                detail=f"Workspace '{request.workspace_name}' not found"
            )
            
        # Delete workspace
        del workspaces[request.workspace_name]
        
        # Update Firestore document
        doc_ref.update({
            "workspaces": workspaces
        })
        
        return DeleteWorkspaceResponse(
            status="success",
            message=f"Workspace '{request.workspace_name}' deleted successfully"
        )
            
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error deleting workspace: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting workspace: {str(e)}"
        )

if __name__ == "__main__":
    # Run the server
    # Note: reload=True watches the project files and restarts the process on any
    # file change. Many components write files under the repository (for
    # example state.json, logs, or vector DB files) which can trigger an
    # endless restart loop. For development use the CLI with --reload when
    # needed; here we disable reload to avoid watch-induced restart storms.
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)


