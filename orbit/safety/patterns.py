from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class RiskPattern:
    pattern: re.Pattern[str]
    tier: Literal["safe", "caution", "destructive", "nuclear"]
    description: str
    production_escalate: bool = False


# ── Filesystem: Safe ─────────────────────────────────────────────────────────
_FS_SAFE = [
    RiskPattern(re.compile(r"^ls\b"), "safe", "list directory"),
    RiskPattern(re.compile(r"^cat\b"), "safe", "display file"),
    RiskPattern(re.compile(r"^head\b"), "safe", "display file head"),
    RiskPattern(re.compile(r"^tail\b"), "safe", "display file tail"),
    RiskPattern(re.compile(r"^wc\b"), "safe", "word/line count"),
    RiskPattern(re.compile(r"^find\b"), "safe", "search files"),
    RiskPattern(re.compile(r"^grep\b"), "safe", "search content"),
    RiskPattern(re.compile(r"^file\b"), "safe", "file type detection"),
    RiskPattern(re.compile(r"^stat\b"), "safe", "file statistics"),
    RiskPattern(re.compile(r"^du\b"), "safe", "disk usage"),
    RiskPattern(re.compile(r"^df\b"), "safe", "filesystem usage"),
    RiskPattern(re.compile(r"^pwd\b"), "safe", "print working directory"),
    RiskPattern(re.compile(r"^echo\b"), "safe", "print text"),
    RiskPattern(re.compile(r"^env\b"), "safe", "show environment"),
    RiskPattern(re.compile(r"^which\b"), "safe", "locate command"),
    RiskPattern(re.compile(r"^whoami\b"), "safe", "current user"),
    RiskPattern(re.compile(r"^hostname\b"), "safe", "show hostname"),
    RiskPattern(re.compile(r"^uname\b"), "safe", "system info"),
    RiskPattern(re.compile(r"^date\b"), "safe", "show date/time"),
    RiskPattern(re.compile(r"^uptime\b"), "safe", "system uptime"),
    RiskPattern(re.compile(r"^free\b"), "safe", "memory usage"),
    RiskPattern(re.compile(r"^ps\b"), "safe", "process list"),
    RiskPattern(re.compile(r"^top\b"), "safe", "process monitor"),
    RiskPattern(re.compile(r"^id\b"), "safe", "user identity"),
    RiskPattern(re.compile(r"^printenv\b"), "safe", "print environment"),
    RiskPattern(re.compile(r"^tree\b"), "safe", "directory tree"),
    RiskPattern(re.compile(r"^less\b"), "safe", "page file"),
    RiskPattern(re.compile(r"^more\b"), "safe", "page file"),
    RiskPattern(re.compile(r"^diff\b"), "safe", "compare files"),
    RiskPattern(re.compile(r"^sort\b"), "safe", "sort input"),
    RiskPattern(re.compile(r"^uniq\b"), "safe", "filter duplicates"),
    RiskPattern(re.compile(r"^cut\b"), "safe", "cut fields"),
    RiskPattern(re.compile(r"^awk\b"), "safe", "text processing"),
    RiskPattern(re.compile(r"^sed\b(?!.*-i)"), "safe", "stream edit (read-only)"),
]

# ── Filesystem: Caution ──────────────────────────────────────────────────────
_FS_CAUTION = [
    RiskPattern(re.compile(r"^mkdir\b"), "caution", "create directory"),
    RiskPattern(re.compile(r"^touch\b"), "caution", "create/update file"),
    RiskPattern(re.compile(r"^cp\b"), "caution", "copy files"),
    RiskPattern(re.compile(r"^mv\b"), "caution", "move/rename files"),
    RiskPattern(re.compile(r"^chmod\b"), "caution", "change permissions"),
    RiskPattern(re.compile(r"^chown\b"), "caution", "change ownership"),
    RiskPattern(re.compile(r"^ln\b"), "caution", "create link"),
    RiskPattern(re.compile(r"^tee\b"), "caution", "write to file"),
    RiskPattern(re.compile(r"^sed\s+-i\b"), "caution", "in-place file edit"),
]

# ── Filesystem: Destructive ──────────────────────────────────────────────────
_FS_DESTRUCTIVE = [
    RiskPattern(re.compile(r"^rm\b"), "destructive", "delete files", production_escalate=True),
    RiskPattern(re.compile(r"^rmdir\b"), "destructive", "delete directory", production_escalate=True),
    RiskPattern(re.compile(r"^shred\b"), "destructive", "securely delete files", production_escalate=True),
]

# ── Filesystem: Nuclear ──────────────────────────────────────────────────────
_FS_NUCLEAR = [
    RiskPattern(re.compile(r"rm\s+-rf\s+/\s*$"), "nuclear", "recursive delete root"),
    RiskPattern(re.compile(r"rm\s+-rf\s+/\w"), "nuclear", "recursive delete from root"),
    RiskPattern(re.compile(r"rm\s+-rf\s+~"), "nuclear", "recursive delete home"),
    RiskPattern(re.compile(r"rm\s+-rf\s+\*"), "nuclear", "recursive delete wildcard"),
    RiskPattern(re.compile(r"mkfs\b"), "nuclear", "format filesystem"),
    RiskPattern(re.compile(r"dd\s+.*of=/dev/"), "nuclear", "write to device"),
    RiskPattern(re.compile(r":\(\)\{.*\}"), "nuclear", "fork bomb"),
]

# ── Git: Safe ────────────────────────────────────────────────────────────────
_GIT_SAFE = [
    RiskPattern(re.compile(r"^git\s+(log|status|diff|show|tag|remote|stash\s+list)\b"), "safe", "git read"),
    RiskPattern(re.compile(r"^git\s+branch\b(?!.*-[dD])"), "safe", "git branch list"),
    RiskPattern(re.compile(r"^git\s+describe\b"), "safe", "git describe"),
    RiskPattern(re.compile(r"^git\s+rev-parse\b"), "safe", "git rev-parse"),
    RiskPattern(re.compile(r"^git\s+ls-files\b"), "safe", "git list files"),
    RiskPattern(re.compile(r"^git\s+blame\b"), "safe", "git blame"),
    RiskPattern(re.compile(r"^git\s+shortlog\b"), "safe", "git shortlog"),
]

# ── Git: Caution ─────────────────────────────────────────────────────────────
_GIT_CAUTION = [
    RiskPattern(re.compile(r"^git\s+add\b"), "caution", "stage changes"),
    RiskPattern(re.compile(r"^git\s+commit\b"), "caution", "create commit"),
    RiskPattern(
        re.compile(r"^git\s+push\b(?!.*--force)(?!.*-f\b)"), "caution", "push to remote", production_escalate=True
    ),
    RiskPattern(re.compile(r"^git\s+pull\b"), "caution", "pull from remote"),
    RiskPattern(re.compile(r"^git\s+fetch\b"), "caution", "fetch from remote"),
    RiskPattern(re.compile(r"^git\s+merge\b"), "caution", "merge branch", production_escalate=True),
    RiskPattern(re.compile(r"^git\s+checkout\b"), "caution", "switch branch/restore"),
    RiskPattern(re.compile(r"^git\s+switch\b"), "caution", "switch branch"),
    RiskPattern(re.compile(r"^git\s+stash\b(?!.*list)"), "caution", "stash changes"),
    RiskPattern(re.compile(r"^git\s+rebase\b"), "caution", "rebase branch", production_escalate=True),
    RiskPattern(re.compile(r"^git\s+cherry-pick\b"), "caution", "cherry-pick commit"),
]

# ── Git: Destructive ─────────────────────────────────────────────────────────
_GIT_DESTRUCTIVE = [
    RiskPattern(re.compile(r"^git\s+reset\s+--hard"), "destructive", "hard reset", production_escalate=True),
    RiskPattern(re.compile(r"^git\s+clean\s+-f"), "destructive", "clean untracked files", production_escalate=True),
    RiskPattern(re.compile(r"^git\s+push\s+.*--force"), "destructive", "force push", production_escalate=True),
    RiskPattern(re.compile(r"^git\s+push\s+.*-f\b"), "destructive", "force push", production_escalate=True),
    RiskPattern(re.compile(r"^git\s+branch\s+-[dD]\b"), "destructive", "delete branch", production_escalate=True),
]

# ── Docker: Safe ─────────────────────────────────────────────────────────────
_DOCKER_SAFE = [
    RiskPattern(re.compile(r"^docker\s+ps\b"), "safe", "list containers"),
    RiskPattern(re.compile(r"^docker\s+images\b"), "safe", "list images"),
    RiskPattern(re.compile(r"^docker\s+inspect\b"), "safe", "inspect object"),
    RiskPattern(re.compile(r"^docker\s+logs\b"), "safe", "view logs"),
    RiskPattern(re.compile(r"^docker\s+stats\b"), "safe", "container stats"),
    RiskPattern(re.compile(r"^docker\s+top\b"), "safe", "container processes"),
    RiskPattern(re.compile(r"^docker\s+info\b"), "safe", "docker info"),
    RiskPattern(re.compile(r"^docker\s+version\b"), "safe", "docker version"),
    RiskPattern(re.compile(r"^docker\s+compose\s+(ps|logs|config)\b"), "safe", "compose read"),
    RiskPattern(re.compile(r"^docker\s+network\s+ls\b"), "safe", "list networks"),
    RiskPattern(re.compile(r"^docker\s+volume\s+ls\b"), "safe", "list volumes"),
]

# ── Docker: Caution ──────────────────────────────────────────────────────────
_DOCKER_CAUTION = [
    RiskPattern(re.compile(r"^docker\s+build\b"), "caution", "build image"),
    RiskPattern(re.compile(r"^docker\s+run\b"), "caution", "run container"),
    RiskPattern(re.compile(r"^docker\s+exec\b"), "caution", "execute in container"),
    RiskPattern(re.compile(r"^docker\s+push\b"), "caution", "push image"),
    RiskPattern(re.compile(r"^docker\s+pull\b"), "caution", "pull image"),
    RiskPattern(re.compile(r"^docker\s+compose\s+up\b"), "caution", "compose up"),
    RiskPattern(re.compile(r"^docker\s+compose\s+build\b"), "caution", "compose build"),
    RiskPattern(re.compile(r"^docker\s+start\b"), "caution", "start container"),
    RiskPattern(re.compile(r"^docker\s+stop\b"), "caution", "stop container"),
    RiskPattern(re.compile(r"^docker\s+restart\b"), "caution", "restart container"),
    RiskPattern(re.compile(r"^docker\s+tag\b"), "caution", "tag image"),
]

# ── Docker: Destructive ──────────────────────────────────────────────────────
_DOCKER_DESTRUCTIVE = [
    RiskPattern(re.compile(r"^docker\s+rm\b"), "destructive", "remove container"),
    RiskPattern(re.compile(r"^docker\s+rmi\b"), "destructive", "remove image"),
    RiskPattern(re.compile(r"^docker\s+compose\s+down\b"), "destructive", "compose down"),
    RiskPattern(re.compile(r"^docker\s+volume\s+rm\b"), "destructive", "remove volume"),
    RiskPattern(re.compile(r"^docker\s+network\s+rm\b"), "destructive", "remove network"),
    RiskPattern(re.compile(r"^docker\s+container\s+prune\b"), "destructive", "prune containers"),
    RiskPattern(re.compile(r"^docker\s+image\s+prune\b"), "destructive", "prune images"),
]

# ── Docker: Nuclear ──────────────────────────────────────────────────────────
_DOCKER_NUCLEAR = [
    RiskPattern(re.compile(r"^docker\s+system\s+prune\b"), "nuclear", "prune everything"),
]

# ── Kubernetes: Safe ─────────────────────────────────────────────────────────
_K8S_SAFE = [
    RiskPattern(re.compile(r"^kubectl\s+get\b"), "safe", "k8s read"),
    RiskPattern(re.compile(r"^kubectl\s+describe\b"), "safe", "k8s describe"),
    RiskPattern(re.compile(r"^kubectl\s+logs\b"), "safe", "k8s logs"),
    RiskPattern(re.compile(r"^kubectl\s+top\b"), "safe", "k8s metrics"),
    RiskPattern(re.compile(r"^kubectl\s+config\s+(view|get-contexts|current-context)\b"), "safe", "k8s config read"),
    RiskPattern(re.compile(r"^kubectl\s+cluster-info\b"), "safe", "k8s cluster info"),
    RiskPattern(re.compile(r"^kubectl\s+api-resources\b"), "safe", "k8s api resources"),
    RiskPattern(re.compile(r"^kubectl\s+explain\b"), "safe", "k8s explain"),
    RiskPattern(re.compile(r"^kubectl\s+version\b"), "safe", "k8s version"),
    RiskPattern(re.compile(r"^helm\s+(list|status|get|history)\b"), "safe", "helm read"),
]

# ── Kubernetes: Caution ──────────────────────────────────────────────────────
_K8S_CAUTION = [
    RiskPattern(re.compile(r"^kubectl\s+apply\b"), "caution", "apply manifest", production_escalate=True),
    RiskPattern(re.compile(r"^kubectl\s+create\b"), "caution", "create resource", production_escalate=True),
    RiskPattern(re.compile(r"^kubectl\s+patch\b"), "caution", "patch resource", production_escalate=True),
    RiskPattern(re.compile(r"^kubectl\s+label\b"), "caution", "label resource"),
    RiskPattern(re.compile(r"^kubectl\s+annotate\b"), "caution", "annotate resource"),
    RiskPattern(re.compile(r"^kubectl\s+scale\b"), "caution", "scale resource", production_escalate=True),
    RiskPattern(re.compile(r"^kubectl\s+rollout\b"), "caution", "manage rollout", production_escalate=True),
    RiskPattern(re.compile(r"^kubectl\s+exec\b"), "caution", "execute in pod"),
    RiskPattern(re.compile(r"^kubectl\s+port-forward\b"), "caution", "port forward"),
    RiskPattern(re.compile(r"^kubectl\s+cp\b"), "caution", "copy to/from pod"),
    RiskPattern(re.compile(r"^kubectl\s+config\s+use-context\b"), "caution", "switch k8s context"),
    RiskPattern(re.compile(r"^kubectl\s+config\s+set-context\b"), "caution", "set k8s context"),
    RiskPattern(re.compile(r"^helm\s+install\b"), "caution", "helm install", production_escalate=True),
    RiskPattern(re.compile(r"^helm\s+upgrade\b"), "caution", "helm upgrade", production_escalate=True),
]

# ── Kubernetes: Destructive ──────────────────────────────────────────────────
_K8S_DESTRUCTIVE = [
    RiskPattern(
        re.compile(r"^kubectl\s+delete\b(?!.*namespace)(?!.*--all)"),
        "destructive",
        "delete k8s resource",
        production_escalate=True,
    ),
    RiskPattern(re.compile(r"^kubectl\s+drain\b"), "destructive", "drain node", production_escalate=True),
    RiskPattern(re.compile(r"^kubectl\s+cordon\b"), "destructive", "cordon node", production_escalate=True),
    RiskPattern(re.compile(r"^helm\s+uninstall\b"), "destructive", "helm uninstall", production_escalate=True),
    RiskPattern(re.compile(r"^helm\s+rollback\b"), "destructive", "helm rollback", production_escalate=True),
]

# ── Kubernetes: Nuclear ──────────────────────────────────────────────────────
_K8S_NUCLEAR = [
    RiskPattern(re.compile(r"^kubectl\s+delete\s+namespace\b"), "nuclear", "delete namespace"),
    RiskPattern(re.compile(r"^kubectl\s+delete\s+.*--all\b"), "nuclear", "delete all resources"),
]

# ── Terraform ────────────────────────────────────────────────────────────────
_TERRAFORM = [
    RiskPattern(re.compile(r"^terraform\s+(init|validate|fmt|show|state\s+list)\b"), "safe", "terraform read"),
    RiskPattern(re.compile(r"^terraform\s+plan\b"), "caution", "terraform plan"),
    RiskPattern(re.compile(r"^terraform\s+apply\b"), "caution", "terraform apply", production_escalate=True),
    RiskPattern(re.compile(r"^terraform\s+import\b"), "caution", "terraform import"),
    RiskPattern(re.compile(r"^terraform\s+state\s+rm\b"), "destructive", "remove from state"),
    RiskPattern(re.compile(r"^terraform\s+destroy\b"), "nuclear", "destroy infrastructure"),
]

# ── SQL ──────────────────────────────────────────────────────────────────────
_SQL = [
    RiskPattern(re.compile(r"SELECT\b", re.IGNORECASE), "safe", "SQL select"),
    RiskPattern(re.compile(r"INSERT\b", re.IGNORECASE), "caution", "SQL insert"),
    RiskPattern(re.compile(r"UPDATE\b", re.IGNORECASE), "caution", "SQL update", production_escalate=True),
    RiskPattern(re.compile(r"ALTER\s+TABLE\b", re.IGNORECASE), "caution", "SQL alter table"),
    RiskPattern(re.compile(r"DELETE\s+FROM\b", re.IGNORECASE), "destructive", "SQL delete", production_escalate=True),
    RiskPattern(re.compile(r"DROP\s+(TABLE|DATABASE|INDEX|VIEW)\b", re.IGNORECASE), "nuclear", "SQL drop"),
    RiskPattern(re.compile(r"TRUNCATE\b", re.IGNORECASE), "nuclear", "SQL truncate"),
]

# ── Misc ─────────────────────────────────────────────────────────────────────
_MISC = [
    RiskPattern(re.compile(r"^curl\b"), "safe", "HTTP request"),
    RiskPattern(re.compile(r"^wget\b"), "safe", "download file"),
    RiskPattern(re.compile(r"^ping\b"), "safe", "network ping"),
    RiskPattern(re.compile(r"^dig\b"), "safe", "DNS lookup"),
    RiskPattern(re.compile(r"^nslookup\b"), "safe", "DNS lookup"),
    RiskPattern(re.compile(r"^traceroute\b"), "safe", "trace route"),
    RiskPattern(re.compile(r"^python\b"), "safe", "run python"),
    RiskPattern(re.compile(r"^node\b"), "safe", "run node"),
    RiskPattern(re.compile(r"^make\b"), "caution", "run make"),
    RiskPattern(re.compile(r"^ssh\b"), "caution", "SSH connection"),
    RiskPattern(re.compile(r"^scp\b"), "caution", "secure copy"),
    RiskPattern(re.compile(r"^rsync\b"), "caution", "sync files"),
    RiskPattern(re.compile(r"^pip\s+install\b"), "caution", "install Python package"),
    RiskPattern(re.compile(r"^npm\s+install\b"), "caution", "install Node package"),
    RiskPattern(re.compile(r"^brew\s+install\b"), "caution", "install Homebrew package"),
    RiskPattern(re.compile(r"^apt\s+(install|upgrade)\b"), "caution", "install apt package"),
    RiskPattern(
        re.compile(r"^systemctl\s+(start|stop|restart|enable|disable)\b"),
        "caution",
        "manage service",
        production_escalate=True,
    ),
    RiskPattern(re.compile(r"^kill\b"), "destructive", "kill process"),
    RiskPattern(re.compile(r"^killall\b"), "destructive", "kill processes by name"),
    RiskPattern(re.compile(r"^sudo\b"), "destructive", "elevated privileges", production_escalate=True),
    RiskPattern(re.compile(r"^reboot\b"), "nuclear", "reboot system"),
    RiskPattern(re.compile(r"^shutdown\b"), "nuclear", "shutdown system"),
    RiskPattern(re.compile(r"^init\s+0\b"), "nuclear", "halt system"),
]

# Production context detection patterns
PRODUCTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bprod(uction)?\b", re.IGNORECASE),
    re.compile(r"\bmain\b"),
    re.compile(r"\bmaster\b"),
    re.compile(r"\brelease/", re.IGNORECASE),
    re.compile(r"\blive\b", re.IGNORECASE),
]


def _by_tier(patterns: list[RiskPattern], tier: str) -> list[RiskPattern]:
    return [p for p in patterns if p.tier == tier]


# All patterns, ordered: nuclear first → destructive → caution → safe
# Most dangerous/specific match found first
PATTERNS: list[RiskPattern] = (
    _FS_NUCLEAR
    + _DOCKER_NUCLEAR
    + _K8S_NUCLEAR
    + _by_tier(_TERRAFORM, "nuclear")
    + _by_tier(_SQL, "nuclear")
    + _by_tier(_MISC, "nuclear")
    + _FS_DESTRUCTIVE
    + _GIT_DESTRUCTIVE
    + _DOCKER_DESTRUCTIVE
    + _K8S_DESTRUCTIVE
    + _by_tier(_TERRAFORM, "destructive")
    + _by_tier(_SQL, "destructive")
    + _by_tier(_MISC, "destructive")
    + _FS_CAUTION
    + _GIT_CAUTION
    + _DOCKER_CAUTION
    + _K8S_CAUTION
    + _by_tier(_TERRAFORM, "caution")
    + _by_tier(_SQL, "caution")
    + _by_tier(_MISC, "caution")
    + _FS_SAFE
    + _GIT_SAFE
    + _DOCKER_SAFE
    + _K8S_SAFE
    + _by_tier(_TERRAFORM, "safe")
    + _by_tier(_SQL, "safe")
    + _by_tier(_MISC, "safe")
)
