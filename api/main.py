import sys
import os
import uuid
import asyncio
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add project root to sys.path to import the orchestrator
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from orchestrator import run_scan

app = FastAPI(title="ScriptSim API")

# Add CORS middleware to allow cross-origin requests from the dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for local development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ScanRequest(BaseModel):
    url: str
    email: str = "test@scriptsim.com"
    password: str = "TestPass123!"
    personas: list[str] = ["kid", "power_user", "parent", "retiree"]
    scan_mode: str = "full"

class ScanResponse(BaseModel):
    scan_id: str
    status: str
    message: str

def trigger_scan_task(url: str, email: str, password: str, scan_id: str, personas: list[str], scan_mode: str):
    """Background task to run the async orchestrator pipeline in a new event loop."""
    try:
        asyncio.run(run_scan(
            target_url=url, 
            login_email=email, 
            login_password=password, 
            scan_id=scan_id,
            personas=personas,
            scan_mode=scan_mode
        ))
    except Exception as e:
        print(f"Scan {scan_id} failed: {e}")

@app.post("/scan", response_model=ScanResponse)
async def create_scan(request: ScanRequest, background_tasks: BackgroundTasks):
    if not request.url:
        raise HTTPException(status_code=400, detail="Target URL is required")
        
    scan_id = str(uuid.uuid4())
    
    # Launch scan in background so the endpoint returns quickly
    background_tasks.add_task(
        trigger_scan_task, 
        request.url, 
        request.email, 
        request.password, 
        scan_id,
        request.personas,
        request.scan_mode
    )
    
    return ScanResponse(
        scan_id=scan_id,
        status="started",
        message="Scan initiated in the background. Check the dashboard for results."
    )

@app.get("/health")
async def health_check():
    return {"status": "ok"}
