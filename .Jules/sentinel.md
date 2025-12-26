## 2024-05-24 - Secure IPC Paths
**Vulnerability:** Use of fixed paths in /tmp for IPC socket and PID file allowed potential symlink attacks and information disclosure.
**Learning:** Hardcoded paths in /tmp are almost always a security risk. Using `XDG_RUNTIME_DIR` or user-specific secure directories is essential.
**Prevention:** Always use dynamic path resolution that respects user permissions and OS standards.
