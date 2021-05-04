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
"""Implements mesos operator"""
import ast
import requests
import json
import mesos.http

from airflow.configuration import conf
from tempfile import TemporaryDirectory
from typing import Dict, Iterable, List, Optional, Union

from airflow.exceptions import AirflowException
from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults


# pylint: disable=too-many-instance-attributes
class MesosOperator(BaseOperator):
    """
    Execute a command inside a docker container and schedule it via apache mesos.

    :param mesos_master: Apache Mesos master leader
    :type mesos_master: str
    :param mesos_principal: Principal to authenticate against the mesos leader
    :type mesos_principal: str
    :param mesos_secret: Secret to authenticate against the mesos leader
    :type mesos_secret: str
    :param image: Docker image from which to create the container.
        If image tag is omitted, "latest" will be used.
    :type image: str
    :param command: Command to be run in the container. (templated)
    :type command: str or list
    :param cpus: Number of CPUs to assign to the container.
        This value gets multiplied with 1024. See
        https://docs.docker.com/engine/reference/run/#cpu-share-constraint
    :type cpus: float
    :param environment: Environment variables to set in the container. (templated)
    :type environment: dict
    :param force_pull: Pull the docker image on every run. Default is False.
    :type force_pull: bool
    :param mem_limit: Maximum amount of memory the container can use.
        Either a float value, which represents the limit in bytes,
        or a string like ``128m`` or ``1g``.
    :type mem_limit: float or str
    :param network_mode: Network mode for the container.
    :type network_mode: str
    :param user: Default user inside the docker container.
    :type user: int or str
    :param volumes: List of volumes to mount into the container, e.g.
        ``['/host/path:/container/path', '/host/path2:/container/path2:ro']``.
    :type volumes: list
    """

    # pylint: disable=too-many-arguments,too-many-locals
    @apply_defaults
    def __init__(
        self,
        *,
        image: str,
        command: Optional[Union[str, List[str]]] = None,
        command_parameter: Optional[Union[str, List[str]]] = None,
        cpus: float = None,
        environment: Optional[Dict] = None,
        force_pull: bool = False,
        memlimit: Optional[Union[float, str]] = None,
        network_mode: Optional[str] = None,
        user: Optional[Union[str, int]] = None,
        volumes: Optional[List[str]] = None,
        airflow_scheduler_url: str = "http://localhost:10000",
        container_type: str = "MESOS",
        **kwargs,
    ) -> None:

        super().__init__(**kwargs)
        self.command = command
        self.command_parameter = command_parameter
        self.cpus = cpus
        self.environment = environment or {}
        self.force_pull = force_pull
        self.image = image
        self.mem_limit = memlimit
        self.network_mode = network_mode
        self.user = user
        self.volumes = volumes or []
        self.airflow_scheduler_url = airflow_scheduler_url
        self.container_type = container_type

        if conf.getboolean('mesos', 'AUTHENTICATE'):
            if not conf.get('mesos', 'DEFAULT_PRINCIPAL'):
                self.log.error("Expecting authentication principal in the environment")
                raise AirflowException("mesos.default_principal not provided in authenticated mode")
            if not conf.get('mesos', 'DEFAULT_SECRET'):
                self.log.error("Expecting authentication secret in the environment")
                raise AirflowException("mesos.default_secret not provided in authenticated mode")
            self.principal = conf.get('mesos', 'DEFAULT_PRINCIPAL')
            self.secret = conf.get('mesos', 'DEFAULT_SECRET')             

    def execute(self, context) -> Optional[str]:
        headers = {
            "Content-Type": "application/json",
            "cache-control": "no-cache",
        }

        data = {}
        data["container_type"] = self.container_type
        data["airflow_task_id"] = self.task_id

        if self.command != None:
            data["command"] = self.command

        if self.image != None:
            data["image"] = self.image

        self.log.info(self)

        response = requests.request(method="POST", 
                                    url=self.airflow_scheduler_url + "/v0/queue_command",
                                    data=json.dumps(data), 
                                    headers=headers)

        self.log.debug(response)

    def attach_container_output(self):
        """
        Streams all output data (e.g. STDOUT/STDERR) to the
        client from the agent.
        """
 
        message = {            
            'type': 'ATTACH_CONTAINER_OUTPUT',
            'attach_container_output': {
                'container_id': self.container_id
            }
        }
 
        req_extra_args = {
            'stream': True,
            'verify': False,
            'additional_headers': {
                'Content-Type': 'application/json',
                'Accept': 'application/recordio',
                'Message-Accept': 'application/json'
            }
        }
 
        try:
            resource = mesos.http.Resource(self.agent_url)
            response = resource.request(
                mesos.http.METHOD_POST,
                data=json.dumps(message),
                retry=False,
                timeout=None,
                auth=self.authentication_header(),
                **req_extra_args)
        except MesosHTTPException as e:
            text = "I/O switchboard server was disabled for this container"
            if e.response.status_code == 500 and e.response.text == text:
                raise CLIException("Unable to attach to a task"
                                   " launched without a TTY")
        raise e

    def authentication_header(self):
        """
        Return the BasicAuth authentication header
        """
        if (self.principal() is not None
                and self._secret() is not None):
            return requests.auth.HTTPBasicAuth(
                self.principal(),
                self.secret()
            )
        return None       
        

