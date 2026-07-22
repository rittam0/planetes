import os
from typing import Optional, Dict, Any
import time
import json
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq

env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "DEMO_KEY")
GROQ_MODEL = "llama-3.3-70b-versatile"

def generate_report(
    conjunction_id: str,
    risk_analysis: Dict[str, Any],
    object_a: Dict[str, Any],
    object_b: Dict[str, Any],
    question: str,
    rag_context: str = ""
) -> Optional[Dict[str, Any]]:
    """Synchronous Groq LLM report generation."""
    if not GROQ_API_KEY or GROQ_API_KEY == "DEMO_KEY":
        print("[Groq] No API key configured")
        return None

    system_prompt = """You are an orbital mechanics expert. Analyze satellite conjunction data and output ONLY valid JSON with this exact schema:
{
  "risk_summary": "1-2 sentence summary",
  "recommended_action": "MONITOR|MANEUVER_ADVISORY|HIGH_ALERT",
  "confidence_rationale": "Which physics inputs drove the score",
  "source_references": ["source 1", "source 2"]
}"""

    rag_section = f"\n\nRelevant orbital mechanics context:\n{rag_context}" if rag_context else ""

    user_prompt = f"""Analyze conjunction {conjunction_id}:
Object A: {object_a.get('name','Unknown')} (alt {object_a.get('altitude_km','N/A')}km, vel {object_a.get('velocity_kms','N/A')}km/s, mass {object_a.get('mass_kg','N/A')}kg)
Object B: {object_b.get('name','Unknown')} (alt {object_b.get('altitude_km','N/A')}km, vel {object_b.get('velocity_kms','N/A')}km/s, mass {object_b.get('mass_kg','N/A')}kg)
Risk: level={risk_analysis.get('risk_level','N/A')}, probability={risk_analysis.get('collision_probability','N/A')}, distance={risk_analysis.get('distance_km','N/A')}km, kinetic_energy={risk_analysis.get('kinetic_energy_j','N/A')}J
Question: {question}{rag_section}"""

    try:
        print(f"[Groq] Calling LLM for {conjunction_id}")
        client = Groq(api_key=GROQ_API_KEY)
        start = time.time()
        resp = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
            max_tokens=500,
            response_format={"type": "json_object"}
        )
        latency = round((time.time() - start) * 1000, 2)
        print(f"[Groq] success latency={latency}ms")
        
        content = resp.choices[0].message.content
        report = json.loads(content)
        report["llm_latency_ms"] = latency
        report["model"] = GROQ_MODEL
        report["rag_augmented"] = bool(rag_context)
        return report
    except Exception as e:
        print(f"[Groq] Exception {type(e).__name__}: {e}")
    
    return None
