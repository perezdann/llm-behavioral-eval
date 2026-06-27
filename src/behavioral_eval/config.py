"""Configuration loader: providers, spec profiles, environment fallback."""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


def load_provider_config(config_path: Optional[Path] = None, spec_path: Optional[Path] = None) -> Dict[str, Any]:
    if config_path and config_path.exists():
        with open(config_path) as f:
            return json.load(f)

    # Look relative to spec_path first (workspace root local/)
    if spec_path:
        for candidate in [
            spec_path.parent / "local" / "llm-providers.json",
            spec_path / "local" / "llm-providers.json",
            spec_path.parent / "llm-providers.json",
        ]:
            if candidate.exists():
                with open(candidate) as f:
                    return json.load(f)

    # Look relative to CWD
    for candidate in [
        Path("local/llm-providers.json"),
        Path("../local/llm-providers.json"),
    ]:
        if candidate.exists():
            with open(candidate) as f:
                return json.load(f)

    base_url = os.getenv("LLM_BASE_URL") or os.getenv("OPENAI_BASE_URL") or "http://localhost:8080/v1"
    api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
    model = os.getenv("LLM_MODEL", "local")

    return {
        "default_provider": "env",
        "providers": {
            "env": {
                "type": "openai-compatible",
                "base_url": base_url,
                "api_key": api_key,
                "model": model,
            }
        },
    }


def get_provider(config: Dict[str, Any], provider_name: Optional[str] = None) -> Dict[str, Any]:
    providers = config.get("providers", {})
    name = provider_name or config.get("default_provider", "env")
    if name not in providers:
        raise ValueError(f"Provider '{name}' not found. Available: {list(providers.keys())}")
    return providers[name]


def load_spec_profile(spec_path: Path) -> Dict[str, Any]:
    """Load a spec profile (eval-profile.json or AGENTS.md-based defaults)."""
    profile_file = spec_path / "eval-profile.json"
    if profile_file.exists():
        with open(profile_file) as f:
            profile = json.load(f)
        profile["_spec_root"] = str(spec_path.resolve())
        return profile

    # Auto-detect: build profile from directory structure
    profile = {"name": spec_path.name, "_spec_root": str(spec_path.resolve())}

    if (spec_path / "AGENTS.md").exists():
        profile.setdefault("spec_files", {})["core"] = "AGENTS.md"
    if (spec_path / "mini" / "core.md").exists():
        profile.setdefault("spec_files", {})["compact"] = "mini/core.md"
    if (spec_path / "evaluation-rubric.md").exists():
        profile.setdefault("spec_files", {})["rubric"] = "evaluation-rubric.md"
    if (spec_path / "roles").is_dir():
        profile["roles_dir"] = "roles"
    if (spec_path / "variants").is_dir():
        profile["variants_dir"] = "variants"

    profile.setdefault("suites", {
        "core_principles": {"count": 20},
        "rubric_dimensions": {"count": 40},
        "roles": {"count": 40},
        "variants": {"count": 25},
        "concrete": {"count": 30, "stratified": True},
    })

    # Default principles and dimensions if not in profile
    profile.setdefault("principles", [
        "Think & Frame Before Acting", "Simplicity & Minimum Viable",
        "Surgical & Precise Changes", "Goal-Driven with Verification",
        "Surface Tradeoffs & Log Decisions", "Verification-First Workflow",
        "Agentic Workflow Discipline",
    ])
    profile.setdefault("rubric_dimensions", [
        "Framing & Assumptions", "Scope Discipline", "Simplicity",
        "Verification", "Tradeoffs",
    ])
    profile.setdefault("roles", [
        "physician", "lawyer", "accountant", "nurse", "mechanic",
        "electronics-technician", "seamstress", "graphic-designer", "architect",
        "domain-specialist", "researcher", "educator", "reviewer",
    ])
    profile.setdefault("variants", [
        "software-development", "research-knowledge", "education-courses",
        "infra-devops", "product-management", "data-analysis", "professional-services",
    ])

    return profile
