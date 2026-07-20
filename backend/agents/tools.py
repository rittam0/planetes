"""Tool definitions for the LangGraph agent."""
from typing import Type
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from backend.db.database import SessionLocal, OrbitalObjectDB, ConjunctionEventDB


class GetObjectInput(BaseModel):
    norad_id: str = Field(description="NORAD catalog ID of the object")


class GetObjectTool(BaseTool):
    name: str = "get_object"
    description: str = "Retrieve orbital data for a satellite or debris object by NORAD ID"
    args_schema: Type[BaseModel] = GetObjectInput

    def _run(self, norad_id: str) -> str:
        db: Session = SessionLocal()
        try:
            obj = db.query(OrbitalObjectDB).filter_by(norad_id=norad_id).first()
            if not obj:
                return f"Object {norad_id} not found in database."
            return (
                f"Object: {obj.name} (NORAD: {obj.norad_id})\n"
                f"Category: {obj.category}\n"
                f"Current altitude: {obj.altitude_km:.1f} km\n"
                f"Current velocity: {obj.velocity_kms:.2f} km/s\n"
                f"Inclination: {obj.inclination_deg:.2f}°\n"
                f"Orbital period: {obj.period_min:.1f} minutes\n"
                f"Last updated: {obj.updated_at.isoformat()}"
            )
        finally:
            db.close()

    async def _arun(self, norad_id: str) -> str:
        return self._run(norad_id)


class GetConjunctionsInput(BaseModel):
    norad_id: str = Field(description="NORAD catalog ID of the primary object")


class GetConjunctionsTool(BaseTool):
    name: str = "get_conjunctions"
    description: str = "Retrieve upcoming close-approach events (conjunctions) for an object"
    args_schema: Type[BaseModel] = GetConjunctionsInput

    def _run(self, norad_id: str) -> str:
        db: Session = SessionLocal()
        try:
            events = db.query(ConjunctionEventDB).filter_by(primary_norad=norad_id).all()
            if not events:
                return f"No upcoming conjunctions found for {norad_id}."

            lines = [f"Found {len(events)} upcoming conjunctions for {norad_id}:"]
            for ev in events:
                lines.append(
                    f"- vs {ev.secondary_name} (NORAD: {ev.secondary_norad})\n"
                    f"  Time: {ev.tca.isoformat()}\n"
                    f"  Miss distance: {ev.min_range_km:.3f} km\n"
                    f"  Max collision probability: {ev.max_probability:.6f}\n"
                    f"  Relative velocity: {ev.relative_velocity_kms:.2f} km/s"
                )
            return "\n\n".join(lines)
        finally:
            db.close()

    async def _arun(self, norad_id: str) -> str:
        return self._run(norad_id)


class ExplainEncounterInput(BaseModel):
    primary_norad: str = Field(description="NORAD ID of primary object")
    secondary_norad: str = Field(description="NORAD ID of secondary object")


class ExplainEncounterTool(BaseTool):
    name: str = "explain_encounter"
    description: str = "Get a structured explanation of a conjunction encounter between two objects"
    args_schema: Type[BaseModel] = ExplainEncounterInput

    def _run(self, primary_norad: str, secondary_norad: str) -> str:
        db: Session = SessionLocal()
        try:
            primary = db.query(OrbitalObjectDB).filter_by(norad_id=primary_norad).first()
            secondary = db.query(OrbitalObjectDB).filter_by(norad_id=secondary_norad).first()

            event = db.query(ConjunctionEventDB).filter_by(
                primary_norad=primary_norad,
                secondary_norad=secondary_norad
            ).first()

            if not event:
                return "No conjunction event found between these objects."

            # Deterministic comparisons
            primary_type = primary.category if primary else "unknown"
            secondary_type = secondary.category if secondary else "unknown"

            # Risk interpretation
            if event.max_probability > 1e-4:
                risk_level = "HIGH"
            elif event.max_probability > 1e-6:
                risk_level = "MODERATE"
            else:
                risk_level = "LOW"

            # Contextual comparison
            geo_altitude = 35786  # GEO altitude in km
            leo_threshold = 2000

            context = ""
            if primary and primary.altitude_km < leo_threshold:
                context = f"Both objects are in Low Earth Orbit (LEO, <{leo_threshold} km), where debris density is highest."
            elif primary and primary.altitude_km > geo_altitude - 500:
                context = f"Objects are near Geostationary orbit (~{geo_altitude} km), a valuable orbital slot."

            return (
                f"ENCOUNTER ANALYSIS\n"
                f"==================\n"
                f"Primary: {event.primary_name} ({primary_type})\n"
                f"Secondary: {event.secondary_name} ({secondary_type})\n"
                f"Time of closest approach: {event.tca.isoformat()}\n"
                f"Miss distance: {event.min_range_km:.3f} km\n"
                f"Relative velocity: {event.relative_velocity_kms:.2f} km/s\n"
                f"Max collision probability: {event.max_probability:.2e}\n"
                f"Risk level: {risk_level}\n"
                f"\n{context}\n"
                f"\nAt {event.relative_velocity_kms:.2f} km/s, even a small debris fragment "
                f"carries significant kinetic energy. A miss distance of {event.min_range_km:.3f} km "
                f"is {'concerning' if event.min_range_km < 1.0 else 'relatively safe'} for orbital operations."
            )
        finally:
            db.close()

    async def _arun(self, primary_norad: str, secondary_norad: str) -> str:
        return self._run(primary_norad, secondary_norad)
