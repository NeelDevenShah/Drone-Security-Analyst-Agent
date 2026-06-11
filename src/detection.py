"""Config-driven fallback object extraction and activity classification."""
import re
from typing import Iterable, List

try:
    from .config import DETECTION_CONFIG
except ImportError:
    from config import DETECTION_CONFIG


def extract_objects_from_keywords(description: str) -> List[str]:
    """Extract normalized object categories using configured CV fallback keywords."""
    if not description:
        return [DETECTION_CONFIG.fallback_object]

    extracted = []
    desc_lower = description.lower()

    for category, keywords in DETECTION_CONFIG.cv_fallback_keywords.items():
        if _contains_any_keyword(desc_lower, keywords):
            extracted.append(category)

    return extracted if extracted else [DETECTION_CONFIG.fallback_object]


def classify_activity_from_rules(objects: Iterable[str]) -> str:
    """Classify fallback activity using configured category combinations."""
    object_set = {obj.lower() for obj in objects}

    for activity, required_objects in DETECTION_CONFIG.cv_fallback_activity_rules:
        if all(required.lower() in object_set for required in required_objects):
            return activity

    return DETECTION_CONFIG.fallback_activity


def _contains_any_keyword(text: str, keywords: Iterable[str]) -> bool:
    """Match keywords as whole words/phrases, avoiding substring false positives."""
    for keyword in keywords:
        pattern = rf"(?<!\w){re.escape(keyword.lower())}(?!\w)"
        if re.search(pattern, text):
            return True
    return False
