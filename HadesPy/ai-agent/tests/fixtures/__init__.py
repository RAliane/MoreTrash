"""Test fixtures for determinism validation.

This module provides deterministic test data for use across all
determinism tests. All fixtures use fixed seeds to ensure
reproducibility.
"""

import json
from pathlib import Path
from typing import Any, Dict, List


def load_fixture(filename: str) -> Any:
    """Load a JSON fixture file.

    Args:
        filename: Name of the fixture file (e.g., 'deterministic_courses.json')

    Returns:
        Parsed JSON data
    """
    fixture_path = Path(__file__).parent / filename
    with open(fixture_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_deterministic_courses() -> List[Dict[str, Any]]:
    """Get deterministic test courses.

    Returns:
        List of course dictionaries
    """
    data = load_fixture('deterministic_courses.json')
    return data['courses']


def get_deterministic_preferences(profile_name: str = None) -> Dict[str, Any]:
    """Get deterministic student preferences.

    Args:
        profile_name: Name of the profile (e.g., 'aerospace_engineer')
                     If None, returns all profiles

    Returns:
        Preference dictionary or all profiles if profile_name is None
    """
    data = load_fixture('deterministic_preferences.json')
    profiles = data['profiles']

    if profile_name is None:
        return profiles

    if profile_name not in profiles:
        raise ValueError(f"Unknown profile: {profile_name}. "
                        f"Available: {list(profiles.keys())}")

    return profiles[profile_name]


def get_all_profile_names() -> List[str]:
    """Get list of all available profile names.

    Returns:
        List of profile name strings
    """
    data = load_fixture('deterministic_preferences.json')
    return list(data['profiles'].keys())


# Fixed seeds for deterministic operations
DETERMINISM_SEED = 42
NUM_ITERATIONS_COGNEE = 3
NUM_ITERATIONS_RANKING = 5
NUM_ITERATIONS_PIPELINE = 20
