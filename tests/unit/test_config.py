import pytest
from v2m.config import Settings

def test_config_loading():
    """Test that configuration loads correctly."""
    config = Settings()
    assert config.whisper.model == "distil-large-v3"
    assert config.whisper.language == "es"
    assert config.gemini.retry_attempts == 3
