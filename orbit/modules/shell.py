from __future__ import annotations

from orbit.modules.base import BaseModule


class ShellModule(BaseModule):
    @property
    def name(self) -> str:
        return "shell"

    @property
    def description(self) -> str:
        return "General shell operations"

    @property
    def commands(self) -> list[str]:
        return ["bash", "sh", "zsh", "echo", "cat", "ls", "find", "grep", "awk", "sed", "sort", "curl", "wget"]

    def get_system_prompt(self) -> str:
        return "You are an expert in Unix/Linux shell commands. Prefer portable POSIX syntax when possible."

    def get_common_failures(self) -> dict[str, str]:
        return {
            "command not found": "The command is not installed or not in PATH. Install it or check your PATH.",
            "Permission denied": "You don't have permission. Try 'chmod' to fix permissions or use 'sudo'.",
            "No such file or directory": "The file or directory does not exist. Check the path.",
            "syntax error": "Shell syntax error. Check quotes, brackets, and command structure.",
            "Argument list too long": "Too many arguments. Use xargs or find -exec instead.",
        }

    def suggest_rollback(self, command: str) -> str | None:
        return None


module = ShellModule()
