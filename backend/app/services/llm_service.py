"""LLM service — generates chaos scenarios from an architecture description.

Supports:
  - provider=openai  →  uses openai Python SDK
  - provider=watsonx →  uses ibm-generative-ai SDK
"""
from __future__ import annotations

import json
import logging
from enum import Enum
from typing import Any

from app.config import settings
from app.schemas import ArchitectureCreate, FaultStep

logger = logging.getLogger(__name__)

FAULT_TYPES = [
    "kill_container",
    "pause_container",
    "network_partition",
    "cpu_stress",
    "memory_stress",
    "inject_latency",
]

SYSTEM_PROMPT = """You are a chaos engineering expert. Given a system architecture description,
generate realistic multi-layered fault-injection scenarios that stress-test the system in ways
human engineers rarely think to combine.

Available fault types:
- kill_container      : Terminates the container process entirely
- pause_container     : Freezes all container processes (SIGSTOP)
- network_partition   : Disconnects the container from its Docker network
- cpu_stress          : Pins CPU usage at a high percentage via stress-ng
- memory_stress       : Allocates memory aggressively via stress-ng
- inject_latency      : Adds network latency using tc netem (requires iproute2 in container)

Output ONLY a valid JSON array. Do not include explanation text before or after.
Each element must follow this schema:
{
  "title": "Short descriptive title",
  "description": "Why this scenario exposes a hidden vulnerability",
  "steps": [
    {
      "step_index": 0,
      "fault_type": "<one of the fault types above>",
      "target_service": "<service name from the architecture>",
      "duration_seconds": <integer 10-120>,
      "parameters": {},
      "description": "What this step does"
    }
  ]
}

Parameters by fault type:
- inject_latency: {"delay_ms": 200, "jitter_ms": 50}
- cpu_stress:     {"cpu_cores": 1, "load_pct": 80}
- memory_stress:  {"memory_mb": 256}
- others:         {}

Ensure each scenario has 2-4 steps targeting different services. Make scenarios compound and non-obvious."""


def _build_user_prompt(arch: ArchitectureCreate, num_scenarios: int) -> str:
    services_desc = "\n".join(
        f"  - {s.name} ({s.type}), depends on: {s.dependencies or 'none'}, "
        f"SLO latency: {s.slo_latency_ms}ms, availability: {s.slo_availability_pct}%"
        for s in arch.services
    )
    return (
        f"Architecture: {arch.name}\n"
        f"Description: {arch.description or 'N/A'}\n"
        f"Services:\n{services_desc}\n\n"
        f"Generate exactly {num_scenarios} chaos scenarios as a JSON array."
    )


def _parse_llm_response(raw: str) -> list[dict[str, Any]]:
    """Extract JSON array from LLM response, tolerating markdown fences."""
    text = raw.strip()
    # Strip markdown fences if present
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(
            l for l in lines if not l.strip().startswith("```")
        )
    # Find the first '[' and last ']'
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON array found in LLM response: {raw[:200]}")
    return json.loads(text[start : end + 1])


def _call_openai(user_prompt: str) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=settings.LLM_API_KEY)
    response = client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
        response_format={"type": "json_object"} if "gpt-4" in settings.LLM_MODEL else None,
    )
    return response.choices[0].message.content or ""


def _call_watsonx(user_prompt: str) -> str:
    from genai import Client, Credentials
    from genai.schema import TextGenerationParameters

    credentials = Credentials(
        api_key=settings.LLM_API_KEY,
        api_endpoint=settings.WATSONX_API_URL,
    )
    client = Client(credentials=credentials)

    full_prompt = f"{SYSTEM_PROMPT}\n\nUser: {user_prompt}\n\nAssistant:"
    response = client.text.generation.create(
        model_id=settings.LLM_MODEL,
        inputs=[full_prompt],
        parameters=TextGenerationParameters(
            max_new_tokens=2048,
            temperature=0.7,
        ),
        project_id=settings.WATSONX_PROJECT_ID,
    )
    return response.results[0].generated_text if response.results else ""


def _mock_scenarios(arch: ArchitectureCreate, num_scenarios: int) -> list[dict[str, Any]]:
    """Return realistic pre-built scenarios when no LLM API key is configured.

    Uses the first 3 service names from the architecture so the scenarios
    look tailored to what the user entered.
    """
    names = [s.name for s in arch.services]
    svc0 = names[0] if len(names) > 0 else "service-a"
    svc1 = names[1] if len(names) > 1 else "service-b"
    svc2 = names[2] if len(names) > 2 else "service-c"

    all_mocks = [
        {
            "title": f"Database Crash During Peak CPU Load on {svc0}",
            "description": (
                f"Kills {svc1} while {svc0} is under heavy CPU pressure. "
                "Exposes missing retry logic and connection-pool exhaustion."
            ),
            "steps": [
                {
                    "step_index": 0,
                    "fault_type": "cpu_stress",
                    "target_service": svc0,
                    "duration_seconds": 60,
                    "parameters": {"cpu_cores": 1, "load_pct": 80},
                    "description": f"Simulate traffic spike on {svc0}",
                },
                {
                    "step_index": 1,
                    "fault_type": "kill_container",
                    "target_service": svc1,
                    "duration_seconds": 30,
                    "parameters": {},
                    "description": f"Abruptly terminate {svc1} during CPU stress",
                },
            ],
        },
        {
            "title": f"Network Partition + Memory Exhaustion",
            "description": (
                f"Disconnects {svc1} from the network while {svc2} exhausts memory. "
                "Tests whether the system degrades gracefully or cascades."
            ),
            "steps": [
                {
                    "step_index": 0,
                    "fault_type": "memory_stress",
                    "target_service": svc2,
                    "duration_seconds": 45,
                    "parameters": {"memory_mb": 256},
                    "description": f"Fill {svc2} RAM to trigger OOM pressure",
                },
                {
                    "step_index": 1,
                    "fault_type": "network_partition",
                    "target_service": svc1,
                    "duration_seconds": 30,
                    "parameters": {},
                    "description": f"Isolate {svc1} from all other services",
                },
            ],
        },
        {
            "title": f"Latency Injection + Process Freeze",
            "description": (
                f"Adds 300ms network jitter to {svc0} then pauses {svc1} entirely. "
                "Reveals timeout misconfigurations and missing circuit breakers."
            ),
            "steps": [
                {
                    "step_index": 0,
                    "fault_type": "inject_latency",
                    "target_service": svc0,
                    "duration_seconds": 40,
                    "parameters": {"delay_ms": 300, "jitter_ms": 100},
                    "description": f"Inject 300ms ±100ms latency on {svc0}",
                },
                {
                    "step_index": 1,
                    "fault_type": "pause_container",
                    "target_service": svc1,
                    "duration_seconds": 20,
                    "parameters": {},
                    "description": f"Freeze {svc1} processes (SIGSTOP)",
                },
                {
                    "step_index": 2,
                    "fault_type": "cpu_stress",
                    "target_service": svc2,
                    "duration_seconds": 30,
                    "parameters": {"cpu_cores": 1, "load_pct": 90},
                    "description": f"Overload {svc2} while {svc1} is frozen",
                },
            ],
        },
    ]
    return all_mocks[:num_scenarios]


def generate_scenarios(arch: ArchitectureCreate, num_scenarios: int = 3) -> list[dict[str, Any]]:
    """Call the configured LLM and return a list of raw scenario dicts.

    Falls back to realistic mock scenarios when LLM_API_KEY is not set —
    so the app is fully usable for demos without an API key.
    """
    if not settings.LLM_API_KEY:
        logger.info("LLM_API_KEY not set — returning mock scenarios for demo mode")
        return _mock_scenarios(arch, num_scenarios)

    user_prompt = _build_user_prompt(arch, num_scenarios)

    for attempt in range(2):
        try:
            if settings.LLM_PROVIDER == "watsonx":
                raw = _call_watsonx(user_prompt)
            else:
                raw = _call_openai(user_prompt)

            scenarios = _parse_llm_response(raw)
            if not isinstance(scenarios, list):
                raise ValueError("LLM did not return a JSON array")
            return scenarios

        except Exception as exc:
            logger.warning("LLM attempt %d failed: %s", attempt + 1, exc)
            if attempt == 1:
                raise

    return []


def generate_narrative(run_summary: dict[str, Any]) -> str:
    """Generate a post-run narrative summary using the LLM."""
    prompt = (
        "You are a site-reliability expert reviewing a chaos engineering run result.\n"
        "Summarize the system's resilience based on these results and give an overall "
        "resilience score from 1 (very fragile) to 10 (highly resilient).\n\n"
        f"Run results:\n{json.dumps(run_summary, indent=2)}\n\n"
        "Provide a concise 2-4 paragraph assessment."
    )
    try:
        if settings.LLM_PROVIDER == "watsonx":
            return _call_watsonx(prompt)
        return _call_openai(prompt)
    except Exception as exc:
        logger.error("Narrative generation failed: %s", exc)
        return "Narrative generation unavailable."
