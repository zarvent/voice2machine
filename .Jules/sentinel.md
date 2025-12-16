# Sentinel Journal 🛡️

## 2024-05-22 - Insecure Temporary Files in Shell Scripts
**Vulnerability:** Shell scripts (`v2m-daemon.sh`) were hardcoding `/tmp/v2m_daemon.log` and `/tmp/v2m_daemon.pid`. This allows for symlink attacks and race conditions where a malicious user could pre-create these files (or symlinks) to overwrite arbitrary files or cause denial of service.
**Learning:** Even when the main application (Python) has secure path logic (`v2m.utils.paths`), auxiliary shell scripts often bypass it and re-implement insecure logic.
**Prevention:** Centralize path resolution logic in a single shell script (`resolve_paths.sh`) that mirrors the secure Python logic, and force all shell scripts to source it.
