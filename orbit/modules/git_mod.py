from __future__ import annotations

from orbit.modules.base import BaseModule


class GitModule(BaseModule):
    @property
    def name(self) -> str:
        return "git"

    @property
    def description(self) -> str:
        return "Git version control operations"

    @property
    def commands(self) -> list[str]:
        return ["git"]

    def get_system_prompt(self) -> str:
        return (
            "You are an expert in Git. Prefer 'git switch' over 'git checkout' for branches. "
            "Always check for uncommitted changes before destructive operations. "
            "Use --no-edit for merge commits when appropriate."
        )

    def get_common_failures(self) -> dict[str, str]:
        return {
            "fatal: not a git repository": "Not inside a git repository. Run 'git init' or cd to a repo.",
            "CONFLICT (content)": "Merge conflict. Edit conflicting files, then 'git add' and 'git commit'.",
            "error: failed to push some refs": "Remote has new changes. Run 'git pull --rebase' first.",
            "error: Your local changes to the following files would be overwritten": (
                "Stash or commit changes first: 'git stash'."
            ),
            "fatal: refusing to merge unrelated histories": "Use --allow-unrelated-histories if intentional.",
            "error: pathspec": "File or branch not found. Check spelling.",
            "fatal: remote origin already exists": "Remote already configured. Use 'git remote set-url origin <url>'.",
            "Everything up-to-date": "Nothing to push. Your branch is up-to-date with remote.",
        }

    def suggest_rollback(self, command: str) -> str | None:
        if "git reset --hard" in command:
            return "git reset --hard HEAD@{1}"
        if "git push --force" in command:
            return "git push --force origin HEAD@{1}:branch-name"
        if "git branch -D" in command or "git branch -d" in command:
            return "git reflog  # find the commit, then: git branch <name> <commit>"
        return None


module = GitModule()
