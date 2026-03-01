from __future__ import annotations

from orbit.modules.base import BaseModule


class DockerModule(BaseModule):
    @property
    def name(self) -> str:
        return "docker"

    @property
    def description(self) -> str:
        return "Docker container operations"

    @property
    def commands(self) -> list[str]:
        return ["docker", "docker-compose"]

    def get_system_prompt(self) -> str:
        return (
            "You are an expert in Docker. Use 'docker compose' (V2) not 'docker-compose' (V1). "
            "Prefer multi-stage builds. Always tag images explicitly."
        )

    def get_common_failures(self) -> dict[str, str]:
        return {
            "Cannot connect to the Docker daemon": (
                "Docker daemon not running. Start Docker Desktop or 'systemctl start docker'."
            ),
            "port is already allocated": "Port conflict. Stop the other container or use a different port.",
            "no space left on device": "Disk full. Run 'docker system prune' to reclaim space.",
            "image not found": "Image doesn't exist locally or in registry. Check the image name and tag.",
            "network not found": "Docker network doesn't exist. Create it with 'docker network create'.",
            "Conflict. The container name": (
                "Container name already in use. Remove it with 'docker rm' or use a different name."
            ),
        }

    def suggest_rollback(self, command: str) -> str | None:
        if "docker compose up" in command:
            return "docker compose down"
        if "docker compose down" in command:
            return "docker compose up -d"
        return None


module = DockerModule()
