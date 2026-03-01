from __future__ import annotations

from orbit.modules.base import BaseModule


class K8sModule(BaseModule):
    @property
    def name(self) -> str:
        return "k8s"

    @property
    def description(self) -> str:
        return "Kubernetes operations"

    @property
    def commands(self) -> list[str]:
        return ["kubectl", "helm", "k9s"]

    def get_system_prompt(self) -> str:
        return (
            "You are an expert in Kubernetes. Always specify namespace explicitly. "
            "Use 'kubectl apply' over 'kubectl create' for declarative management. "
            "Check rollout status after deployments."
        )

    def get_common_failures(self) -> dict[str, str]:
        return {
            "connection refused": "Cannot reach the Kubernetes API server. Check your kubeconfig and cluster status.",
            "the server doesn't have a resource type": "Resource type not recognized. Check API version and spelling.",
            "forbidden": "RBAC permission denied. Check your service account permissions.",
            "ImagePullBackOff": "Cannot pull container image. Check image name, tag, and registry credentials.",
            "CrashLoopBackOff": "Container keeps crashing. Check logs with 'kubectl logs <pod>'.",
            "Pending": "Pod stuck in Pending. Check resource limits, node capacity, and PVC bindings.",
            "error: no matches for kind": "Resource kind not found. Check the API group and version.",
            "OOMKilled": "Container ran out of memory. Increase memory limits in the pod spec.",
        }

    def suggest_rollback(self, command: str) -> str | None:
        if "kubectl apply -f" in command:
            manifest = command.split("-f")[-1].strip().split()[0] if "-f" in command else ""
            if manifest:
                return f"kubectl delete -f {manifest}"
        if "kubectl scale" in command:
            return "kubectl rollout undo deployment/<name>"
        return None


module = K8sModule()
