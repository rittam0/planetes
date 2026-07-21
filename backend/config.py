import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the same directory as this file (absolute path)
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

KEEPTRACK_API_KEY = os.getenv("KEEPTRACK_API_KEY", "DEMO_KEY")
NASA_API_KEY = os.getenv("NASA_API_KEY", "DEMO_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "DEMO_KEY")
