import importlib
import sys
import types
import unittest
from unittest.mock import Mock, patch

import requests


class FakeBaseOperator:
    def __init__(self, task_id=None, dag=None, **kwargs):
        self.task_id = task_id
        self.dag_id = getattr(dag, "dag_id", "test_dag")
        self.log = Mock()


class MesosOperatorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        airflow = types.ModuleType("airflow")
        configuration = types.ModuleType("airflow.configuration")
        exceptions = types.ModuleType("airflow.exceptions")
        models = types.ModuleType("airflow.models")
        configuration.conf = Mock()
        configuration.conf.get.return_value = "http://localhost:11000"
        exceptions.AirflowException = RuntimeError
        models.BaseOperator = FakeBaseOperator
        sys.modules.update({
            "airflow": airflow,
            "airflow.configuration": configuration,
            "airflow.exceptions": exceptions,
            "airflow.models": models,
        })
        cls.module = importlib.import_module("avmesos_airflow_provider.operators.mesos")

    def operator(self, **kwargs):
        return self.module.MesosOperator(task_id="run", **kwargs)

    def response(self, payload, status=200):
        response = Mock()
        response.json.return_value = payload
        response.raise_for_status.side_effect = None if status < 400 else requests.HTTPError("http")
        return response

    def test_payload_normalizes_shell_command_and_resources(self):
        operator = self.operator(
            image="alpine:3.20", command="echo hello", cpus=0.1,
            mem_limit="128m", attributes=["airflow:true"],
            environment={"NAME": "test"},
        )
        payload = operator._payload()
        self.assertEqual(payload["command"], ["/bin/sh", "-c", "echo hello"])
        self.assertEqual(payload["cpus"], 0.1)
        self.assertEqual(payload["mem_limit"], "128m")
        self.assertEqual(payload["environment"], {"NAME": "test"})

    @patch("requests.sleep", create=True)
    @patch("requests.get")
    @patch("requests.post")
    def test_execute_waits_for_and_returns_finished_task(self, post, get, sleep):
        post.return_value = self.response("Ok")
        get.return_value = self.response({"status": {"state": "TASK_FINISHED"}})
        operator = self.operator(image="alpine:3.20", command=["echo", "ok"], poll_interval=0)
        result = operator.execute({})
        self.assertEqual(result["status"]["state"], "TASK_FINISHED")
        post.assert_called_once()
        self.assertEqual(post.call_args.kwargs["json"]["command"], ["echo", "ok"])

    @patch("requests.get")
    @patch("requests.post")
    def test_execute_raises_for_failed_task(self, post, get):
        post.return_value = self.response("Ok")
        get.return_value = self.response({"status": {"state": "TASK_FAILED"}})
        with self.assertRaises(RuntimeError):
            self.operator(image="alpine", command="false", poll_interval=0).execute({})

    def test_payload_contains_docker_options(self):
        payload = self.operator(
            image="alpine", command=["echo", "ok"], force_pull=True,
            network_mode="bridge", user="nobody", volumes=["data:/data"],
        )._payload()
        self.assertTrue(payload["force_pull"])
        self.assertEqual(payload["network_mode"], "bridge")
        self.assertEqual(payload["user"], "nobody")
        self.assertEqual(payload["volumes"], ["data:/data"])

    @patch("requests.post")
    def test_execute_raises_for_queue_http_error(self, post):
        post.return_value = self.response({}, status=500)
        with self.assertRaises(RuntimeError):
            self.operator(image="alpine", command="true").execute({})

    @patch("requests.get")
    @patch("requests.post")
    def test_execute_raises_for_poll_http_error(self, post, get):
        post.return_value = self.response("Ok")
        get.return_value = self.response({}, status=503)
        with self.assertRaises(RuntimeError):
            self.operator(image="alpine", command="true").execute({})

    @patch("requests.get")
    @patch("requests.post")
    @patch("time.monotonic", side_effect=[0, 0, 2])
    @patch("time.sleep")
    def test_execute_raises_on_timeout(self, sleep, monotonic, post, get):
        post.return_value = self.response("Ok")
        get.return_value = self.response({})
        with self.assertRaisesRegex(RuntimeError, "Timed out"):
            self.operator(image="alpine", command="true", startup_timeout=1).execute({})

    def test_test_dag_has_mesos_operator(self):
        with open("docs/examples/dags/mesos_operator_test.py", encoding="utf-8") as dag_file:
            source = dag_file.read()
        self.assertIn("MesosOperator", source)
        self.assertIn('task_id="run_on_mesos"', source)


if __name__ == "__main__":
    unittest.main()
