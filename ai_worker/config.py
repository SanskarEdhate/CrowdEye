import os
import uuid
from pathlib import Path
from dotenv import load_dotenv

# Load root or backend .env if available
root_dir = Path(__file__).resolve().parent.parent
load_dotenv(root_dir / ".env")
load_dotenv(root_dir / "backend" / ".env")

# Network & Service Targets
API_BASE_URL = os.getenv("API_BASE_URL", os.getenv("BACKEND_URL", "http://localhost:8000"))
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", os.getenv("SUPABASE_KEY", ""))

# AI Model & Inference Parameters
MODEL_NAME = os.getenv("YOLO_MODEL", "yolov8n.pt")
DEVICE = os.getenv("AI_DEVICE", "cpu")  # "cuda" if GPU is available
CONF_THRESHOLD = float(os.getenv("CONF_THRESHOLD", "0.45"))
IOU_THRESHOLD = float(os.getenv("IOU_THRESHOLD", "0.5"))

# Adaptive Frame Sampling Parameters (TASK 2)
ADAPTIVE_SAMPLE_NORMAL = int(os.getenv("ADAPTIVE_SAMPLE_NORMAL", "2"))        # Every 2nd frame in normal load
ADAPTIVE_SAMPLE_HIGH_LOAD = int(os.getenv("ADAPTIVE_SAMPLE_HIGH_LOAD", "5"))    # Every 5th frame under high load
HIGH_LOAD_LATENCY_THRESHOLD_MS = float(os.getenv("HIGH_LOAD_MS", "80.0"))

# Demo Mode Flag (TASK 11)
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() in ("true", "1", "yes")

# Worker Identity & Paths
WORKER_ID = f"ai-worker-{str(uuid.uuid4())[:8]}"
LOG_DIR = root_dir / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "ai_worker.log"
