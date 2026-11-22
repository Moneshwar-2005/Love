"""
LOVE Voice Personality, SSML builder, and voice profile registry (Phase 06).
"""

import re
from typing import Dict, List, Optional
from backend.app.config.settings import get_settings
from backend.app.voice.schemas import VoiceProfile


# Default Canonical Profile for LOVE
LOVE_CLASSIC_PROFILE = VoiceProfile(
    id="love_classic",
    name="LOVE Classic (Indian English Female)",
    gender="female",
    accent="Indian English",
    language_code="en-IN",
    description=(
        "An intelligent, elegant, calm, confident, warm and natural female voice with "
        "authentic Indian English pronunciation and subtle futuristic cinematic elegance."
    ),
    speaking_rate=1.0,
    pitch=0.0,
    style="calm, elegant, confident, warm",
    provider_voice_map={
        "azure": "en-IN-NeerjaNeural",
        "elevenlabs": "love_indian_female_v1",
        "piper": "en_IN-cmu_indic-medium",
        "mock": "mock_love_female_in"
    }
)

LOVE_EXPRESSIVE_PROFILE = VoiceProfile(
    id="love_expressive",
    name="LOVE Expressive (Engaging Female)",
    gender="female",
    accent="Indian English",
    language_code="en-IN",
    description="Warm, lively, and articulate Indian English female voice for deep conversational engagement.",
    speaking_rate=1.05,
    pitch=2.0,
    style="warm, articulate, engaging",
    provider_voice_map={
        "azure": "en-IN-AnanyaNeural",
        "elevenlabs": "love_indian_expressive_v1",
        "piper": "en_IN-cmu_indic-medium",
        "mock": "mock_love_female_in"
    }
)

_REGISTERED_PROFILES: Dict[str, VoiceProfile] = {
    "love_classic": LOVE_CLASSIC_PROFILE,
    "love_expressive": LOVE_EXPRESSIVE_PROFILE,
}


def get_active_voice_profile(profile_id: Optional[str] = None) -> VoiceProfile:
    """
    Retrieves the configured VoiceProfile instance.
    Falls back to settings.VOICE_DEFAULT_PERSONALITY or 'love_classic'.
    """
    settings = get_settings()
    target_id = profile_id or settings.VOICE_DEFAULT_PERSONALITY
    return _REGISTERED_PROFILES.get(target_id, LOVE_CLASSIC_PROFILE)


def list_available_profiles() -> List[VoiceProfile]:
    """Returns all registered personality profiles."""
    return list(_REGISTERED_PROFILES.values())


def build_ssml(
    text: str,
    profile: Optional[VoiceProfile] = None,
    provider: str = "azure"
) -> str:
    """
    Constructs clean, W3C-compliant SSML with natural conversational pacing,
    appropriate punctuation pauses, and provider-specific voice tag.
    """
    prof = profile or get_active_voice_profile()
    voice_name = prof.provider_voice_map.get(provider, "en-IN-NeerjaNeural")

    # Clean text of XML special characters
    clean_text = (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )

    # Insert slight natural pauses after periods and commas for measured pacing
    # Avoid inserting consecutive breaks
    paced_text = re.sub(r"([.!?])\s+", r'\1 <break time="220ms"/> ', clean_text)
    paced_text = re.sub(r"([,;:])\s+", r'\1 <break time="120ms"/> ', paced_text)

    # Format rate and pitch
    rate_pct = int((prof.speaking_rate - 1.0) * 100)
    rate_str = f"{rate_pct:+d}%" if rate_pct != 0 else "+0%"
    pitch_str = f"{int(prof.pitch):+d}%" if prof.pitch != 0 else "+0%"

    ssml = (
        f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" '
        f'xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="{prof.language_code}">\n'
        f'  <voice name="{voice_name}">\n'
        f'    <prosody rate="{rate_str}" pitch="{pitch_str}">\n'
        f'      {paced_text}\n'
        f'    </prosody>\n'
        f'  </voice>\n'
        f'</speak>'
    )
    return ssml


# Known Voice Catalogs for Inspection
PROVIDER_VOICE_CATALOGS = {
    "azure": [
        {
            "voice_id": "en-IN-NeerjaNeural",
            "name": "Neerja (Neural)",
            "locale": "en-IN",
            "gender": "Female",
            "description": "Warm, confident, and professional Indian English neural voice (Default LOVE profile)"
        },
        {
            "voice_id": "en-IN-AnanyaNeural",
            "name": "Ananya (Neural)",
            "locale": "en-IN",
            "gender": "Female",
            "description": "Engaging and clear Indian English neural voice"
        },
        {
            "voice_id": "en-IN-PrabhatNeural",
            "name": "Prabhat (Neural)",
            "locale": "en-IN",
            "gender": "Male",
            "description": "Clear and steady Indian English male neural voice"
        }
    ],
    "elevenlabs": [
        {
            "voice_id": "love_indian_female_v1",
            "name": "LOVE Custom (ElevenLabs)",
            "locale": "en-IN",
            "gender": "Female",
            "description": "High-fidelity expressive Indian English voice clone"
        }
    ],
    "piper": [
        {
            "voice_id": "en_IN-cmu_indic-medium",
            "name": "CMU Indic Indian English (Piper)",
            "locale": "en-IN",
            "gender": "Female",
            "description": "Fast local on-device VITS model for Indian English"
        }
    ],
    "mock": [
        {
            "voice_id": "mock_love_female_in",
            "name": "Mock LOVE Indian English Female",
            "locale": "en-IN",
            "gender": "Female",
            "description": "Deterministic local test voice synthesizer"
        }
    ]
}
