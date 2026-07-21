import os
from dotenv import load_dotenv

load_dotenv()

KEEPTRACK_API_KEY = os.getenv("KEEPTRACK_API_KEY", "DEMO_KEY")
NASA_API_KEY = os.getenv("NASA_API_KEY", "DEMO_KEY")
KEEPTRACK_BASE_URL = "https://api.keeptrack.space/v4"
NASA_BASE_URL = "https://api.nasa.gov/neo/rest/v1"
