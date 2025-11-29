import pytest
from v2m.config import Settings

def test_config_loading():
    """Test that configuration loads correctly."""
    config = Settings()
    # Model name should match config.toml (currently large-v3-turbo)
    assert config.whisper.model == "large-v3-turbo"
    assert config.whisper.language == "auto"
    assert config.gemini.retry_attempts == 3
