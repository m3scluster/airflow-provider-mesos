"""
Apache Mesos Provider to scheduler Apache Airflow DAG's under Mesos.
"""
#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

from queue import Queue
from typing import Any, Dict, Optional, List
from threading import Thread

import time
import threading
import json
import urllib3
import ast
import prometheus_client as prom

from avmesos.client import MesosClient
from airflow.configuration import conf
from airflow.exceptions import AirflowException
from airflow.executors.base_executor import BaseExecutor
from airflow.models.taskinstance import TaskInstanceKey
from airflow.utils.session import provide_session
from airflow.utils.state import State
from flask import Flask, request, Response
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
from waitress import serve

FRAMEWORK_CONNID_PREFIX = "mesos_framework_"

AIRFLOW_QUEUE_GAUGE = prom.Gauge('airflow_queue_gauge', 'Amount of tasks in Airflow queue')
AIRFLOW_MESOS_QUEUE_GAUGE = prom.Gauge('airflow_mesos_queue_gauge', 'Amount of tasks already send to mesos')

urllib3.disable_warnings()

app = Flask(__name__)
auth = HTTPBasicAuth()
api_username = ""
api_password = ""

CommandType = List[str]

def get_framework_name():
    """Get the mesos framework name if its set in airflow.cfg"""
    return conf.get("mesos", "FRAMEWORK_NAME")


# pylint: disable=too-many-nested-blocks
# pylint: disable=too-many-instance-attributes
class AirflowMesosScheduler(MesosClient):
    """
    Airflow Mesos scheduler implements mesos scheduler interface
    to schedule airflow tasks on mesos
    Basically, it schedules a command like
    'airflow run <dag_id> <task_instance_id> <start_date> --local -p=<pickle>'
    to run on a mesos slave
    """

    # pylint: disable=super-init-not-called
    def __init__(
        self, executor, task_queue, result_queue, task_cpu: float = 0.1, task_mem: float = 256.0, task_disk: float = 1000.0
    ):
        self.task_queue = task_queue
        self.result_queue = result_queue
        self.task_cpu = task_cpu
        self.task_mem = task_mem
        self.task_disk = task_disk
        self.task_counter = 0
        self.task_key_map: Dict[str, str] = {}
        self.task_restart: Dict[str, str] = {}
        self.log = executor.log
        self.client = executor.client
        self.executor = executor
        self.driver = None
        self.tasks: Dict[str, str] = {}
        self.suppress = False

        if not conf.get("mesos", "DOCKER_IMAGE_SLAVE"):
            self.log.error("Expecting docker image for  mesos executor")
            raise AirflowException(
                "mesos.slave_docker_image not provided for mesos executor"
            )

        self.mesos_slave_docker_image = conf.get("mesos", "DOCKER_IMAGE_SLAVE")
        self.mesos_docker_volume_driver = conf.get("mesos", "DOCKER_VOLUME_DRIVER")
        self.mesos_docker_volume_dag_name = conf.get("mesos", "DOCKER_VOLUME_DAG_NAME")
        self.mesos_docker_environment = conf.get("mesos", "DOCKER_ENVIRONMENT", fallback="")
        self.mesos_docker_network_mode = conf.get("mesos", "DOCKER_NETWORK_MODE", fallback="HOST")
        self.mesos_docker_volume_dag_container_path = conf.get("mesos", "DOCKER_VOLUME_DAG_CONTAINER_PATH")
        self.mesos_docker_volume_logs_name = conf.get("mesos", "DOCKER_VOLUME_LOGS_NAME")
        self.mesos_docker_volume_logs_container_path = conf.get("mesos", "DOCKER_VOLUME_LOGS_CONTAINER_PATH")
        self.mesos_docker_sock = conf.get("mesos", "DOCKER_SOCK")
        self.mesos_fetch_uri = conf.get("mesos", "MESOS_FETCH_URI", fallback="")
        self.mesos_fetch_uri_username = conf.get("mesos", "MESOS_FETCH_URI_USERNAME", fallback="root")
        self.mesos_attributes = eval(conf.get("mesos", "MESOS_ATTRIBUTES", "[]"))

        self.database_sql_alchemy_conn = conf.get("database", "SQL_ALCHEMY_CONN")
        self.core_fernet_key = conf.get("core", "FERNET_KEY")
        self.logging_logging_level = conf.get("logging", "LOGGING_LEVEL")
        self.logging_log_filename_template = conf.get("logging", "LOG_FILENAME_TEMPLATE")
        self.command_shell = str(
            conf.get("mesos", "COMMAND_SHELL", fallback=True)
        ).lower()

        heartbeat_thread = threading.Thread(target=self.heartbeat_loop)
        heartbeat_thread.daemon = True
        heartbeat_thread.start()


    def heartbeat_loop(self):
        while True:
            self.log.debug("Heartbeat Loop")
            time.sleep(60)


    def resource_heartbeat(self, heartbeat):
        """If we got a heartbeat, run checks"""

        """Set prometheus metric"""
        AIRFLOW_MESOS_QUEUE_GAUGE.set(self.task_queue.qsize())

        self.log.debug("Heartbeat")
        if self.task_queue.empty():
            if not self.suppress:
                self.log.info("Suppress Mesos Framework")
                self.driver.suppress()
                self.suppress = True
        else:
            if self.suppress:
                self.log.info("Revive Mesos Framework")
                self.driver.revive()
                self.suppress = False

    def resource_offers(self, offers):
        """If we got a offer, run a queued task"""
        offer_options = {
            "Filters": {
                "RefuseSeconds": 120.0
            }
        }
        if (not self.task_queue.empty()):
            for index in range(len(offers)):
                offer = offers[index]
                if not self.run_job(offer):
                     offertmp = offer.get_offer()
                     self.log.info("Declined Offer: %s", offertmp["id"]["value"])
                     offer.decline(options=offer_options)
        else:
            for index in range(len(offers)):
                offer = offers[index]
                offertmp = offer.get_offer()
                self.log.info("Declined Offer: %s", offertmp["id"]["value"])
                offer.decline(options=offer_options)

    def convert_memory_to_float(self, memory_str):
        memory_str = memory_str.lower()
        if memory_str.endswith('g'):
            memory_val = float(memory_str[:-1])
            memory_val *= 1024  # Convert from GB to MB
        elif memory_str.endswith('m'):
            memory_val = float(memory_str[:-1])

        return memory_val

    def check_mesos_attributes(self, mesos_attributes, offer):
        # convert offer in Dictionary: {name: value}
        offer_dict = {
            attr["name"].lower(): attr["text"]["value"].lower()
            for attr in offer
            if "name" in attr and "text" in attr and "value" in attr["text"]
        }

        def match_condition(condition):
            if ':' not in condition:
                return False
            key, value = condition.split(':', 1)
            return offer_dict.get(key.lower()) == value.lower()

        # 1. normal cases (without ?:)
        normal_conditions = [a for a in mesos_attributes if '?:' not in a]
        for attr in normal_conditions:
            if not match_condition(attr):
                return False

        # 2. fallback cases (with ?:)
        fallback_conditions = [a for a in mesos_attributes if '?:' in a]
        for attr in fallback_conditions:
            first, fallback = attr.split('?:', 1)

            if first not in normal_conditions:
                if match_condition(first):
                    return False
                if not match_condition(fallback):
                    return False

        return True

    # pylint: disable=too-many-branches
    def run_job(self, mesos_offer):
        """Start a queued Airflow task in Mesos"""
        offer = mesos_offer.get_offer()
        tasks = []
        option = {}
        offer_cpus = 0.1
        offer_mem = 256.0
        offer_disk = 1000.0
        container_type = "DOCKER"
        cpu = self.task_cpu
        disk = self.task_disk
        image = self.mesos_slave_docker_image
        mesos_attributes = self.mesos_attributes
        airflow_task_id = None
        attribute_airflow = "false"  """ have to be string """
        self.task_cpu = float(conf.get("mesos", "TASK_CPU", fallback=0.1))
        self.task_mem = float(conf.get("mesos", "TASK_MEMORY", fallback=256.0))
        self.task_disk = float(conf.get("mesos", "TASK_DISK", fallback=1000.0))

        if (not self.task_queue.empty()):
            key, cmd, executor_config = self.task_queue.get()
            tid = self.task_counter
            self.task_counter += 1

            old_executor_config = executor_config

            if executor_config:
                try:
                    self.log.info("Executor Config: %s", executor_config)
                    self.task_cpu = executor_config.get("cpus", cpu)
                    self.task_mem = self.convert_memory_to_float(executor_config.get("mem_limit", "256m"))
                    self.task_disk = executor_config.get("disk", disk)

                    self.mesos_attributes = executor_config.get("attributes")
                    if len(self.mesos_attributes) > 0:
                      self.mesos_attributes = self.mesos_attributes + mesos_attributes
                    else:
                      selr.mesos_attributes = mesos_attributes

                    image = executor_config.get("image", self.mesos_slave_docker_image)
                    container_type = executor_config.get("container_type", "DOCKER")
                    airflow_task_id = executor_config.get("airflow_task_id", None)
                except Exception as e:
                    self.log.error("Error parsing executor_config: %s", str(e))
                    executor_config["airflow_task_id"] = None

            else:
                executor_config["airflow_task_id"] = None

            if airflow_task_id is None:
                airflow_task_id = "airflow." + str(tid)

            # get CPU, mem and disk from offer
            for resource in offer["resources"]:
                if resource["name"] == "cpus":
                    offer_cpus = resource["scalar"]["value"]
                elif resource["name"] == "mem":
                    offer_mem = resource["scalar"]["value"]
                elif resource["name"] == "disk":
                    offer_disk = resource["scalar"]["value"]

            # set the airflow_task_id as executor config
            executor_config["airflow_task_id"] = airflow_task_id

            if hasattr(key, 'execution_date'):
                name = key.dag_id + "_" + key.task_id + "_" + str(key.execution_date.date()) + ":" + str(key.execution_date.time())
            else:
                name = key.dag_id + "_" + key.task_id

            self.log.info("Received offer %s with cpus: %f and mem: %f and disk: %f for task %s (%s)", offer["id"]["value"], offer_cpus, offer_mem, offer_disk, airflow_task_id, name)

            if len(self.mesos_attributes) > 0:
                if "attributes" in offer:
                    if not self.check_mesos_attributes(self.mesos_attributes, offer["attributes"]):
                        self.log.info("Offered node is not valid for this mesos job. %s (%s)", airflow_task_id, offer["id"]["value"])
                        self.task_queue.put((key, cmd, old_executor_config))
                        return False

                else:
                    self.log.info("Offered node is not valid for airflow jobs. %s (%s)", airflow_task_id, offer["id"]["value"])
                    self.log.debug("return false > name: %s", name)
                    self.task_queue.put((key, cmd, old_executor_config))
                    return False

            # if the resources does not match, add the task again
            if float(offer_cpus) < float(self.task_cpu):
                self.log.info("Offered CPU's for task %s are not enough: got: %f need: %f - %s", airflow_task_id, offer_cpus, self.task_cpu, offer["id"]["value"])
                self.log.debug("return false > name: %s", name)
                self.task_queue.put((key, cmd, old_executor_config))
                return False
            if float(offer_mem) < float(self.task_mem):
                self.log.info("Offered MEM's for task %s are not enough: got: %f need: %f - %s", airflow_task_id, offer_mem, self.task_mem, offer["id"]["value"])
                self.log.debug("return false > name: %s", name)
                self.task_queue.put((key, cmd, old_executor_config))
                return False
            if float(offer_disk) < float(self.task_disk):
                self.log.info("Offered DISK's for task %s are not enough: got: %f need: %f - %s", airflow_task_id, offer_disk, self.task_disk, offer["id"]["value"])
                self.log.debug("return false > name: %s", name)
                self.task_queue.put((key, cmd, old_executor_config))
                return False

            self.task_key_map[airflow_task_id] = key
            self.task_restart[airflow_task_id] = 0

            self.log.info("Launching task %s using offer %s", airflow_task_id, offer["id"]["value"])
            self.result_queue.put((key, State.QUEUED))

            task = {
                "name": name,
                "task_id": {"value": airflow_task_id },
                "agent_id": {"value": offer["agent_id"]["value"]},
                "resources": [
                    {
                        "name": "cpus",
                        "type": "SCALAR",
                        "scalar": {"value": self.task_cpu},
                    },
                    {
                        "name": "mem",
                        "type": "SCALAR",
                        "scalar": {"value": self.task_mem},
                    },
                    {
                        "name": "disk",
                        "type": "SCALAR",
                        "scalar": {"value": self.task_disk},
                    },
                ],
                "command": {
                    "shell": self.command_shell,
                    "environment": {
                        "variables": [
                            {
                                "name": "AIRFLOW__DATABASE__SQL_ALCHEMY_CONN",
                                "value": self.database_sql_alchemy_conn,
                            },
                            {
                                "name": "AIRFLOW__CORE__SQL_ALCHEMY_CONN",
                                "value": self.database_sql_alchemy_conn,
                            },
                            {
                                "name": "AIRFLOW__CORE__FERNET_KEY",
                                "value": self.core_fernet_key,
                            },
                            {
                                "name": "AIRFLOW__CORE__LOAD_EXAMPLES",
                                "value": "false",
                            },
                            {
                                "name": "AIRFLOW__LOGGING__LOGGING_LEVEL",
                                "value": self.logging_logging_level,
                            },
                            {
                                "name": "AIRFLOW__LOGGING__LOG_FILENAME_TEMPLATE",
                                "value": self.logging_log_filename_template,
                            },
                        ]
                    },
                    "value": " ".join(cmd),
                },
                "container": {
                    "type": container_type,
                    "volumes": [
                        {
                            "container_path": self.mesos_docker_volume_dag_container_path,
                            "mode": "RW",
                            "source": {
                                "type": "DOCKER_VOLUME",
                                "docker_volume": {
                                    "driver": self.mesos_docker_volume_driver,
                                    "name": self.mesos_docker_volume_dag_name,
                                },
                            },
                        },
                        {
                            "container_path": self.mesos_docker_volume_logs_container_path,
                            "mode": "RW",
                            "source": {
                                "type": "DOCKER_VOLUME",
                                "docker_volume": {
                                    "driver": self.mesos_docker_volume_driver,
                                    "name": self.mesos_docker_volume_logs_name,
                                },
                            },
                        },
                    ],
                    "docker": {
                        "image": image,
                        "network": self.mesos_docker_network_mode.upper(),
                        "force_pull_image": "true",
                        "privileged": "true",
                        "parameters": [
                            {
                                "key": "volume",
                                "value": self.mesos_docker_sock
                                + ":/var/run/docker.sock",
                            }
                        ],
                    },
                },
            }

            self.log.debug(json.dumps(task, indent=4))

            # fetch dags from uri
            if len(self.mesos_fetch_uri) > 0:
                sand_box_env = {
                    "name": "AIRFLOW__CORE__DAGS_FOLDER",
                    "value": "/mnt/mesos/sandbox",
                }
                task["command"]["environment"]["variables"].append(sand_box_env)
                dag_file = cmd[8].replace('DAGS_FOLDER/', '')
                task["command"]["uris"] = [{
                    "value": self.mesos_fetch_uri + "/" + dag_file,
                    "extract": False,
                    "executable": False,
                    "cache": False,
                    "outputfile": dag_file,
                }]
                task["command"]["user"] = self.mesos_fetch_uri_username

            # concat custom docker environment variables if they are configured
            if len(self.mesos_docker_environment) > 0:
                docker_env = ast.literal_eval(self.mesos_docker_environment)
                len_task = len(docker_env)
                i = 0
                while i < len_task:
                    task["command"]["environment"]["variables"].append(docker_env[i])
                    i += 1

            # if the container would be UCR, we can attach tty
            if container_type == "MESOS":
                task["container"]["tty_info"] = {
                    "window_size": {
                        "rows": 80,
                        "columns": 80,
                    },
                }

            option = {"Filters": {"RefuseSeconds": "0.5"}}

            tasks.append(task)
        if len(tasks) > 0:
            mesos_offer.accept(tasks, option)
            return True
        else:
            mesos_offer.decline()
            return False

    def subscribed(self, driver):
        """
        Subscribe to Mesos Master

        """
        self.driver = driver

    def status_update(self, update):
        """Update the Status of the Tasks. Based by Mesos Events."""
        task_id = update["status"]["task_id"]["value"]
        task_state = update["status"]["state"]

        self.log.info("Task %s is in state %s", task_id, task_state)

        if task_id not in self.task_key_map:
            self.log.info("Task %s is in not int key map", task_id)
            return

        key = self.task_key_map[task_id]

        if task_state == "TASK_RUNNING":
            self.log.info("Task Running: %s", task_id)
            self.result_queue.put((key, State.RUNNING))
            self.tasks[task_id] = update
            return

        if task_state in ("TASK_KILLED", "TASK_FAILED", "TASK_ERROR"):
            self.result_queue.put((key, State.FAILED))
            del self.task_restart[task_id]
            self.cleanupQueues(task_id)
            return

        if task_state in ("TASK_LOST"):
            if self.task_restart[task_id] <= 3:
                self.result_queue.put((key, State.NONE))
                self.task_restart[task_id] += 1
            else:
                self.result_queue.put((key, State.FAILED))
                del self.task_restart[task_id]

            self.cleanupQueues(task_id)


    def get_task_info(self, task_id):
        """Return the container_info of the given task_id"""
        if task_id in self.tasks:
            return self.tasks[task_id]

        return None

    def cleanupQueues(self, task_id):
        self.log.debug("cleanup task: %s", task_id)
        if task_id in self.tasks:
            del self.tasks[task_id]

        if task_id in self.task_key_map:
            del self.task_key_map[task_id]


class MesosExecutor(BaseExecutor):
    """
    MesosExecutor allows distributing the execution of task
    instances to multiple mesos workers.

    Apache Mesos is a distributed systems kernel which abstracts
    CPU, memory, storage, and other compute resources away from
    machines (physical or virtual), enabling fault-tolerant and
    elastic distributed systems to easily be built and run effectively.
    See http://mesos.apache.org/
    """

    class MesosFramework(threading.Thread):
        """MesosFramework class to start the threading"""

        def __init__(self, client):
            super().__init__(target=self)
            self.client = client
            self.stop = False

        def run(self):
            try:
                self.client.register()
            except KeyboardInterrupt:
                print("Stop requested by user, stopping framework....")

    def __init__(self):
        super().__init__()
        self.commands_to_run = []
        self.task_queue = Queue()
        self.result_queue = Queue()
        self.driver = None
        self.client = None
        self.mesos_framework = None
        self.master_urls = None

    @provide_session
    def start(self, session=None):
        """Setup and start routine to connect with the mesos master"""
        master = conf.get("mesos", "MASTER")

        framework_name = get_framework_name()
        framework_id = None
        framework_role = conf.get("mesos", "FRAMEWORK_ROLE", fallback="airflow")

        task_cpu = conf.getfloat("mesos", "TASK_CPU", fallback=0.1)
        task_memory = conf.getfloat("mesos", "TASK_MEMORY", fallback=256.0)
        framework_failover_timeout = conf.getint("mesos", "FAILOVER_TIMEOUT", fallback=604800)

        if conf.getboolean("mesos", "CHECKPOINT", fallback=True):
            framework_checkpoint = True

            if conf.get("mesos", "FAILOVER_TIMEOUT"):
                # Import here to work around a circular import error
                # pylint: disable=import-outside-toplevel
                from airflow.models import Connection

                # Query the database to get the ID of the Mesos Framework, if available.
                conn_id = FRAMEWORK_CONNID_PREFIX + framework_name
                connection = (
                    session.query(Connection).filter_by(conn_id=conn_id).first()
                )
                if connection is not None:
                    # Set the Framework ID to let the scheduler reconnect
                    # with running tasks.
                    framework_id = connection.extra

        else:
            framework_checkpoint = False

        self.log.info(
            "MesosFramework master : %s, name : %s, cpu : %f, mem : %f, checkpoint : %s, id : %s",
            master,
            framework_name,
            task_cpu,
            task_memory,
            framework_checkpoint,
            framework_id,
        )

        self.master_urls = "http://" + master
        if conf.getboolean("mesos", "MESOS_SSL", fallback=False):
          self.master_urls = "https://" + master

        self.client = MesosClient(
            mesos_urls=self.master_urls.split(","),
            frameworkName=framework_name,
            frameworkId=None,
        )

        self.client.set_role(framework_role)

        if framework_failover_timeout:
            self.client.set_failover_timeout(framework_failover_timeout)
        if framework_checkpoint:
            self.client.set_checkpoint(framework_checkpoint)

        if conf.getboolean("mesos", "AUTHENTICATE"):
            if not conf.get("mesos", "DEFAULT_PRINCIPAL"):
                self.log.error("Expecting authentication principal in the environment")
                raise AirflowException(
                    "mesos.default_principal not provided in authenticated mode"
                )
            if not conf.get("mesos", "DEFAULT_SECRET"):
                self.log.error("Expecting authentication secret in the environment")
                raise AirflowException(
                    "mesos.default_secret not provided in authenticated mode"
                )
            self.client.principal = conf.get("mesos", "DEFAULT_PRINCIPAL")
            self.client.secret = conf.get("mesos", "DEFAULT_SECRET")

        driver = AirflowMesosScheduler(self, self.task_queue, self.result_queue, task_cpu, task_memory)
        self.driver = driver
        self.client.max_reconnect = 100
        self.client.on(MesosClient.SUBSCRIBED, driver.subscribed)
        self.client.on(MesosClient.UPDATE, driver.status_update)
        self.client.on(MesosClient.OFFERS, driver.resource_offers)
        self.client.on(MesosClient.HEARTBEAT, driver.resource_heartbeat)


        self.mesos_framework = MesosExecutor.MesosFramework(self.client)
        self.mesos_framework.start()

        # start the framework api
        # set api credentials

        app.add_url_rule(
            "/v0/queue_command",
            "queue_command",
            self.api_queue_command,
            methods=["POST"],
        )
        app.add_url_rule(
            "/v0/task/<task_id>",
            "task/<task_id>",
            self.api_get_task_info,
            methods=["GET"],
        )
        app.add_url_rule(
            "/v0/dags",
            "dags",
            self.api_get_dag_queue,
            methods=["GET"],
        )
        app.add_url_rule(
            "/v0/agent/<agent_id>",
            "agent/<agent_id>",
            self.api_get_agent_address,
            methods=["GET"],
        )


        Thread(target=serve, args=[app], daemon=True, kwargs={"port": "11000"}).start()
        prom.start_http_server(8100)



    def sync(self) -> None:
        """Updates states of the tasks."""

        """Set prometheus metric"""
        AIRFLOW_QUEUE_GAUGE.set(self.task_queue.qsize())

        self.log.debug("Update state of tasks")
        if self.running:
            self.log.debug("self.running: %s", self.running)

        while not self.result_queue.empty():
            results = self.result_queue.get()
            key, state = results
            if key is None:
                return
            if state == "success":
                self.log.info("tasks successfull %s", key)
            if state == "failed":
                self.log.info("tasks failed %s", key)
            self.change_state(*results)

    def execute_async(
        self,
        key: TaskInstanceKey,
        command: CommandType,
        queue: str | None = None,
        executor_config: Any | None = None,
    ):
        """Execute Tasks"""
        self.log.info(
            "Add task %s with command %s with TaskInstance %s",
            key,
            command,
            executor_config,
        )
        self.validate_command(command)
        self.task_queue.put((key, command, executor_config))


    def end(self) -> None:
        """Called when the executor shuts down"""
        self.log.info("Shutting down Mesos Executor")
        # Both queues should be empty...
        self.task_queue = Queue()
        self.result_queue = Queue()
        self.task_queue.join()
        self.result_queue.join()
        self.client.stop = True
        self.driver.tearDown()
        self.mesos_framework.stop = True

    def terminate(self):
        """Terminate the executor is not doing anything."""
        self.end()

    ########## API ##########

    @auth.verify_password
    def verify_api_password(username, password):
        api_username = conf.get("mesos", "API_USERNAME", fallback="user")
        api_password = generate_password_hash(conf.get("mesos", "API_PASSWORD", fallback="password"))

        if username == api_username and check_password_hash(api_password, password):
           return username

        return None


    def api_queue_command_error(self, message):
        """Error message handling for queue_command"""
        self.log.error(message)

        return message

    def api_queue_command(self):
        """
        Queue Command via API

        Example: curl --header "Content-Type: application/json" -X POST -d
        '{ "command": "test", "image": "alpine" }' 127.0.0.1:10000/v0/queue_command
        """

        data = json.loads(request.data)
        error, command = None, None

        if "command" in data:
            command = data["command"]
        else:
            error = self.api_queue_command_error(
                "Expecting command in queue_command call"
            )

        if error is not None:
            response = Response(error, status=400, headers={})
        else:
            self.log.info("Queue task with command %s and %s", command, data)
            self.task_queue.put((None, command, data))
            response = Response("Ok", status=200, headers={})
        # Send it
        return response

    def api_get_task_info(self, task_id):
        """
        Get Mesos TASK Info via API

        Example: curl -X GET 127.0.0.1:10000/v0/task/<task_id>
        """
        task_info = self.driver.get_task_info(task_id)

        response = Response(
            json.dumps(task_info), status=200, mimetype="application/json"
        )
        return response

    @auth.login_required
    def api_get_dag_queue(self):
        """
        Get Airflow DAG queue

        Example: curl -X GET 127.0.0.1:10000/v0/dags
        """
        l = list(self.task_queue.queue)
        a = self.list_to_json(l)
        response = Response(
            str(json.dumps(a, default=str)), status=200, mimetype="application/json"
        )
        return response

    def list_to_json(self, liste):
        ret = []
        for i in liste:
            ## (TaskInstanceKey(dag_id='docker_dag2', task_id='docker_command1', run_id='manual__2022-07-29T15:32:54.865408+00:00', try_number=1),

            ## ['airflow', 'tasks', 'run', 'docker_dag2', 'docker_command1', 'manual__2022-07-29T15:32:54.865408+00:00', '--local', '--subdir', 'DAGS_FOLDER/dag.py'], {'cpus': 7.5, 'mem_limit': 32768}), (TaskInstanceKey(dag_id='docker_dag2', task_id='docker_command2', run_id='manual__2022-07-29T15:32:54.865408+00:00', try_number=1), ['airflow', 'tasks', 'run', 'docker_dag2', 'docker_command2', 'manual__2022-07-29T15:32:54.865408+00:00', '--local', '--subdir', 'DAGS_FOLDER/dag.py'], {'cpus': 2.0, 'mem_limit': 2048}), (TaskInstanceKey(dag_id='docker_dag2', task_id='docker_command1', run_id='manual__2022-07-29T15:34:38.821409+00:00', try_number=1), ['airflow', 'tasks', 'run', 'docker_dag2', 'docker_command1', 'manual__2022-07-29T15:34:38.821409+00:00', '--local', '--subdir', 'DAGS_FOLDER/dag.py'], {'cpus': 7.5, 'mem_limit': 32768}), (TaskInstanceKey(dag_id='docker_dag2', task_id='docker_command2', run_id='manual__2022-07-29T15:34:38.821409+00:00', try_number=1), ['airflow', 'tasks', 'run', 'docker_dag2', 'docker_command2', 'manual__2022-07-29T15:34:38.821409+00:00', '--local', '--subdir', 'DAGS_FOLDER/dag.py'],
            ## {'cpus': 2.0, 'mem_limit': 2048})]
            tmp = dict()
            tmp["dag_id"] = i[0][0]
            tmp["task_id"] = i[0][1]
            tmp["run_id"] = i[0][2]
            tmp["try_number"] = i[0][3]
            tmp["MesosExecutor"] = i[2]
            ret.append(tmp)
        return ret

    def api_get_agent_address(self, agent_id):
        """
        Given a master and an agent id, return the agent address
        by checking the /slaves endpoint of the master.
        """

        http = urllib3.PoolManager()
        http_response = http.request(
            "GET",
            self.master_urls + "/master/slaves",
            headers=self.authentication_header(),
            timeout=5,
        )
        data = http_response.data.decode("utf-8")

        if data is not None:
            data = json.loads(data)
            for agent in data["slaves"]:
                if agent["id"] == agent_id:
                    data = {"hostname": agent["hostname"], "port": str(agent["port"])}
                    response = Response(
                        json.dumps(data), status=200, mimetype="application/json"
                    )
                    return response

        response = Response(None, status=200, mimetype="application/json")
        return response

    def authentication_header(self):
        """
        Return the BasicAuth authentication header
        """
        if self.client.principal is not None and self.client.secret is not None:
            headers = urllib3.make_headers(
                basic_auth=self.client.principal + ":" + self.client.secret
            )
            return headers
        return None
