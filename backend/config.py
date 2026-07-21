import os
from dotenv import load_dotenv

load_dotenv()

KEEPTRACK_API_KEY = os.getenv("KEEPTRACK_API_KEY", "DEMO_KEY")
NASA_API_KEY = os.getenv("NASA_API_KEY", "DEMO_KEY")
