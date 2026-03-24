import os

# Adjust these to your environment
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
INTEGRITY_STORAGE_ROOT = os.path.join(REPO_ROOT, ".integrity")

# Temporary; orchestrator/meta-governor will own this later
CRITICAL_FILES = [
    "core/contracts.py",
    "security/code_integrity.py",
]
