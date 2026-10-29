"""
profanity_filter.py — Multi-lingual profanity and offensive language detector for SafeRoad.

Designed specifically to avoid the 'Scunthorpe problem' (e.g. false positives like
'nasser' containing 'ass', 'classic', 'grass', 'mass', 'pass', 'cockpit', 'basement').

Uses strict word-boundary matching and token extraction across English, Hindi/Urdu, and Telugu.
"""

import re
from typing import Tuple, List

# List of offensive terms (matched strictly on word boundaries \b...\b)
OFFENSIVE_TERMS = {
    # English
    'ass', 'asshole', 'bastard', 'bitch', 'bitches', 'bullshit', 'crap',
    'cunt', 'cunts', 'damn', 'dick', 'dicks', 'fag', 'faggot', 'fuck',
    'fucker', 'fucking', 'fucked', 'motherfucker', 'piss', 'pissed',
    'prick', 'pussy', 'shit', 'shitty', 'slut', 'sluts', 'twat', 'wanker',
    'whore', 'whores',

    # Hindi / Urdu
    'bhenchod', 'behenchod', 'bhenchode', 'bc', 'madarchod', 'mc',
    'chutiya', 'chutiye', 'choot', 'chootiya', 'harami', 'haraami',
    'kamina', 'kamine', 'laude', 'lavde', 'lawde', 'lodu', 'lund',
    'gand', 'gaand', 'gandu', 'gaandu', 'bhosdi', 'bhosdike', 'bhosdika',
    'saala', 'sala', 'kutta', 'kutiya', 'randi', 'raand', 'chod', 'chodu',
    'teri maa', 'maa ki aankh',

    # Telugu
    'lanja', 'lanjakodaka', 'lanjamunda', 'dengu', 'dengey', 'dengudu',
    'modda', 'moddalo', 'puka', 'puku', 'pukulo', 'naa kodaka', 'naakodaka',
    'vedhava', 'sulli', 'guddha', 'gudha', 'dongana kodaka',
}

# Compile a single optimized regex with word boundaries
_PATTERN = re.compile(
    r'\b(?:' + '|'.join(re.escape(w) for w in sorted(OFFENSIVE_TERMS, key=len, reverse=True)) + r')\b',
    re.IGNORECASE
)


def contains_profanity(text: str) -> Tuple[bool, List[str]]:
    """
    Check if the provided text contains offensive terms.

    Returns:
        (has_profanity: bool, matched_terms: List[str])

    Examples:
        contains_profanity("Nasser road near hospital") -> (False, [])
        contains_profanity("Fix this damn pothole you ass") -> (True, ['damn', 'ass'])
        contains_profanity("Rey chutiya pothole ikkada") -> (True, ['chutiya'])
    """
    if not text:
        return False, []

    # Clean punctuation and normalize spacing for token checking
    matches = _PATTERN.findall(text)
    if matches:
        # Deduplicate while preserving case-insensitive unique list
        unique_matches = list(dict.fromkeys(m.lower() for m in matches))
        return True, unique_matches

    return False, []


def sanitize_or_validate(text: str, field_name: str = "Description") -> Tuple[bool, str]:
    """
    Validate input text. If profanity is found, returns (False, user_friendly_error_message).
    Otherwise returns (True, "").
    """
    has_bad_words, bad_words = contains_profanity(text)
    if has_bad_words:
        censored_preview = ", ".join(f"'{w}'" for w in bad_words)
        return False, (
            f"Your {field_name.lower()} contains inappropriate or offensive language ({censored_preview}). "
            f"SafeRoad is a municipal reporting platform monitored directly by GHMC engineers and traffic police; "
            f"please maintain respectful language."
        )
    return True, ""
