import os
import httpx
from typing import Optional, Dict, Any
import time
import json
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "DEMO_KEY")
GROQ_BASE = "https://api.groq.com/openai/v1"
GROQ_MODEL = "llama-3.3-70b-versatile"

async def generate_report(
    conjunction_id: str,
    risk_analysis: Dict[str, Any],
    object_a: Dict[str, Any],
    object_b: Dict[str, Any],
    question: str,
    rag_context: str = ""
) -> Optional[Dict[str, Any]]:
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
        print(f"[Groq] Calling LLM for {conjunction_id} with RAG context")
        async with httpx.AsyncClient(timeout=60.0) as client:
            start = time.time()
            resp = await client.post(
                f"{GROQ_BASE}/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": GROQ_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.2,
                    "max_tokens": 500,
                    "response_format": {"type": "json_object"}
                }
            )
            latency = round((time.time() - start) * 1000, 2)
            print(f"[Groq] status={resp.status_code} latency={latency}ms")
            
            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                report = json.loads(content)
                report["llm_latency_ms"] = latency
                report["model"] = GROQ_MODEL
                report["rag_augmented"] = bool(rag_context)
                return report
            elif resp.status_code == 401:
                print(f"[Groq] 401 - invalid API key")
            elif resp.status_code == 429:
                print(f"[Groq] 429 - rate limited")
            else:
                print(f"[Groq] Error {resp.status_code}: {resp.text[:100]}")
    except httpx.TimeoutException:
        print("[Groq] Timeout after 60s")
    except Exception as e:
        print(f"[Groq] Exception {type(e).__name__}: {e}")
    
    return None
