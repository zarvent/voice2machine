import toml
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'
BASE_DIR = Path(__file__).resolve().parent.parent.parent

def load_config():
    """Loads the configuration from config.toml."""
    config_path = BASE_DIR / "config.toml"
    if not config_path.is_file():
        raise FileNotFoundError(f"Configuration file not found at {config_path}")

    with open(config_path, "rb") as f:
        return toml.load(f)

config = load_config()
