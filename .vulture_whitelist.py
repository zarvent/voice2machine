# Vulture whitelist for V2M
# Lista de código que parece no usado pero es necesario

# Pydantic requires 'cls' parameter in settings_customise_sources
_.cls  # src/v2m/config.py

# CQRS pattern - commands are serialized and dispatched
_.listen_to  # Used by command bus reflection

# IPC protocol constants - used by client
_.PING
_.SHUTDOWN
