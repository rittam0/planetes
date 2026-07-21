from fastapi import APIRouter
import random

router = APIRouter(prefix="/api")

@router.get("/conjunctions")
async def get_conjunctions(limit: int = 100):
    conjunctions = []
    for i in range(min(5, limit)):
        conjunctions.append({
            "id": f"conj-{i}",
            "primary_norad": str(25544 + i),
            "primary_name": f"Object-{i}A",
            "secondary_norad": str(25544 + i + 100),
            "secondary_name": f"Object-{i}B",
            "tca": "2024-07-25T12:00:00Z",
            "max_probability": round(random.random() * 0.01, 6),
            "min_range_km": round(random.uniform(0.5, 10), 2),
            "relative_velocity_kms": round(random.uniform(5, 15), 2)
        })
    return {"conjunctions": conjunctions, "total": len(conjunctions)}
