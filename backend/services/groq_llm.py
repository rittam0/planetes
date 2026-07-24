import json
import os
import time
from typing import Any, Dict


GROQ_MODEL = "llama-3.3-70b-versatile"


def generate_report(
    selected_object: Dict[str, Any],
    deterministic_analysis: Dict[str, Any],
    system_instruction: str,
) -> Dict[str, Any]:
    """Generate structured JSON lazily, with explicit failure classifications."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key == "DEMO_KEY":
        return {"status": "missing_key", "report": None, "latency_ms": None}

    try:
        from groq import (
            APIConnectionError,
            APIStatusError,
            AuthenticationError,
            Groq,
            RateLimitError,
        )
    except ImportError:
        return {"status": "sdk_unavailable", "report": None, "latency_ms": None}

    prompt = {
        "object": selected_object,
        "deterministic_analysis": deterministic_analysis,
        "required_schema": {
            "summary": "string",
            "interpretation": "string",
            "recommendation": "string",
            "numeric_facts": deterministic_analysis["numeric_facts"],
        },
    }
    start = time.perf_counter()
    try:
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"{system_instruction} Return only JSON matching the supplied schema. "
                        "Copy numeric_facts exactly; do not add unsupported numbers."
                    ),
                },
                {"role": "user", "content": json.dumps(prompt, default=str)},
            ],
            temperature=0.1,
            max_tokens=600,
            response_format={"type": "json_object"},
        )
        latency = round((time.perf_counter() - start) * 1000, 2)
        content = response.choices[0].message.content
        try:
            report = json.loads(content or "")
        except (json.JSONDecodeError, TypeError):
            return {"status": "malformed_json", "report": None, "latency_ms": latency}
        if not isinstance(report, dict):
            return {"status": "schema_failure", "report": None, "latency_ms": latency}
        return {"status": "success", "report": report, "latency_ms": latency}
    except AuthenticationError:
        status = "authentication_error"
    except RateLimitError:
        status = "rate_limit"
    except APIConnectionError as exc:
        status = "timeout" if "timeout" in str(exc).lower() else "connection_error"
    except APIStatusError:
        status = "api_error"
    except Exception:
        status = "unexpected_error"
    return {
        "status": status,
        "report": None,
        "latency_ms": round((time.perf_counter() - start) * 1000, 2),
    }
