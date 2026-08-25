"""Airflow operator for running one command as a Mesos task."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Union

import requests
from airflow.configuration import conf
from airflow.exceptions import AirflowException
from airflow.models import BaseOperator


class MesosOperator(BaseOperator):
    """Run a Docker/Mesos container through the Mesos executor API."""

    template_fields = ("command", "environment")

    def __init__(
        self, *, image: str, command: Optional[Union[str, List[str]]] = None,
        cpus: Optional[float] = None, environment: Optional[Dict[str, str]] = None,
        force_pull: bool = False, mem_limit: Optional[Union[float, str]] = None,
        memlimit: Optional[Union[float, str]] = None, disk: Optional[float] = None,
        attributes: Optional[List[str]] = None, network_mode: Optional[str] = None,
        user: Optional[Union[str, int]] = None, volumes: Optional[List[str]] = None,
        airflow_scheduler_url: Optional[str] = None, poll_interval: float = 2.0,
        startup_timeout: float = 300.0, **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.image = image
        self.command = command
        self.cpus = cpus
        self.environment = environment or {}
        self.force_pull = force_pull
        self.mem_limit = mem_limit if mem_limit is not None else memlimit
        self.disk = disk
        self.attributes = attributes or []
        self.network_mode = network_mode
        self.user = user
        self.volumes = volumes or []
        self.airflow_scheduler_url = (airflow_scheduler_url or conf.get(
            "mesos", "OPERATOR_API_URL", fallback="http://localhost:11000"
        )).rstrip("/")
        self.poll_interval = poll_interval
        self.startup_timeout = startup_timeout

    @staticmethod
    def _command_as_list(command: Optional[Union[str, List[str]]]) -> List[str]:
        if command is None:
            return []
        if isinstance(command, str):
            return ["/bin/sh", "-c", command]
        return [str(part) for part in command]

    def _payload(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "airflow_task_id": "airflow.{}.{}".format(self.dag_id, self.task_id),
            "container_type": "DOCKER", "command": self._command_as_list(self.command),
            "image": self.image, "force_pull": self.force_pull,
            "environment": self.environment, "attributes": self.attributes,
        }
        for name, value in (("cpus", self.cpus), ("mem_limit", self.mem_limit),
                            ("disk", self.disk), ("network_mode", self.network_mode),
                            ("user", self.user), ("volumes", self.volumes)):
            if value is not None:
                payload[name] = value
        return payload

    def execute(self, context: Any) -> Optional[Dict[str, Any]]:
        payload = self._payload()
        task_id = payload["airflow_task_id"]
        endpoint = self.airflow_scheduler_url
        self.log.info("Queue Mesos task %s using image %s", task_id, self.image)
        try:
            response = requests.post(endpoint + "/v0/queue_command", json=payload, timeout=30)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise AirflowException("Unable to queue Mesos task {}: {}".format(task_id, exc)) from exc

        deadline = time.monotonic() + self.startup_timeout
        while time.monotonic() < deadline:
            try:
                status_response = requests.get(endpoint + "/v0/task/" + task_id, timeout=30)
                status_response.raise_for_status()
                status = status_response.json()
            except (requests.RequestException, ValueError) as exc:
                raise AirflowException("Unable to read Mesos task {}: {}".format(task_id, exc)) from exc
            if status:
                state = status.get("status", {}).get("state")
                if state == "TASK_FINISHED":
                    return status
                if state in {"TASK_FAILED", "TASK_ERROR", "TASK_KILLED", "TASK_LOST", "TASK_UNREACHABLE"}:
                    raise AirflowException("Mesos task {} finished in state {}: {}".format(task_id, state, status))
            time.sleep(self.poll_interval)
        raise AirflowException("Timed out waiting for Mesos task {}".format(task_id))

    def on_kill(self) -> None:
        self.log.warning("Mesos executor API has no task-kill endpoint for %s", self.task_id)