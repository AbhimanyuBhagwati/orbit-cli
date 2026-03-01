from __future__ import annotations

from orbit.modules.base import BaseModule


class FilesystemModule(BaseModule):
    @property
    def name(self) -> str:
        return "filesystem"

    @property
    def description(self) -> str:
        return "File and directory operations"

    @property
    def commands(self) -> list[str]:
        return ["rm", "cp", "mv", "mkdir", "rmdir", "touch", "chmod", "chown", "ln"]

    def get_system_prompt(self) -> str:
        return "You are an expert in filesystem operations. Prefer 'cp -r' for directories. Use 'rm -i' for safety."

    def get_common_failures(self) -> dict[str, str]:
        return {
            "No such file or directory": "Path does not exist. Check spelling and use 'ls' to verify.",
            "Permission denied": "Insufficient permissions. Check file ownership and permissions with 'ls -la'.",
            "Directory not empty": "Cannot remove non-empty directory. Use 'rm -r' if intentional.",
            "File exists": "Target file already exists. Use '-f' to overwrite or choose a different name.",
            "Read-only file system": "Filesystem is mounted read-only. Remount with write permissions.",
        }

    def suggest_rollback(self, command: str) -> str | None:
        return None


module = FilesystemModule()
