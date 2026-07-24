from fastapi import APIRouter

router = APIRouter(prefix="/api")


@router.get("/conjunctions")
async def get_conjunctions():
    """Conjunction screening is intentionally unavailable in V1."""
    return {
        "encounters": [],
        "total": 0,
        "data_status": "unavailable",
        "message": (
            "No operational conjunction feed is configured. Planetes V1 does not "
            "estimate collision probability from object positions alone."
        ),
    }
