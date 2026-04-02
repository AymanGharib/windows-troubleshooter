"""
Builds incident-native prompts with selected skills and explicit tool guidance.
"""

from __future__ import annotations

import json
from typing import Any

from app.agent.incident_skills import render_skill_section, select_incident_skills


def build_incident_prompt(incident: dict[str, Any]) -> str:
    """Build the runtime user prompt for an incident investigation."""
    selected_skills = select_incident_skills(incident)
    incident_json = json.dumps(incident, ensure_ascii=False, indent=2)
    skill_ids = ", ".join(skill.skill_id for skill in selected_skills)

    return (
        "Investigate this Windows incident using the incident payload, the selected skills, "
        "and only the minimum tools needed.\n\n"
        f"Selected skills: {skill_ids}\n\n"
        "Rules for this run:\n"
        "- Start from the incident payload before calling any tool.\n"
        "- Use the selected skills as your operating instructions for this incident type.\n"
        "- Each selected skill tells you when to use tools and which tools are preferred.\n"
        "- If evidence is weak, say what is missing instead of guessing.\n"
        "- Do not remediate automatically. Investigate and recommend next actions only.\n"
        "- Return valid JSON only.\n\n"
        "Selected skill guidance:\n"
        f"{render_skill_section(selected_skills)}\n\n"
        "Incident payload:\n"
        f"{incident_json}\n"
    )
