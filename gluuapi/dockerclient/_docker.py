# -*- coding: utf-8 -*-
# Copyright (c) 2015 Gluu
#
# All rights reserved.

import json

import docker.errors
from docker import Client

from ..log import create_file_logger
from ..registry import Registry
from ..utils import run_in_shell


class Docker(object):
    def __init__(self, config, logger=None):
        self.logger = logger or create_file_logger()
        self.machine_conf = config
        self.registry_base_url = Registry().registry_base_url
        self.docker = Client(base_url=self.machine_conf['base_url'],
                             tls=self.machine_conf['tls'])

    def image_exists(self, name):
        """Checks whether a docker image exists.

        :param name: Image name
        :returns: ``True`` if image exists, otherwise ``False``
        """
        images = self.docker.images(name)
        return True if images else False

    def setup_container(self, name, image, env=None, port_bindings=None,
                        volumes=None, dns=None, dns_search=None, ulimits=None):
        self.logger.info("creating container {!r}".format(name))

        image = "{}/{}".format(self.registry_base_url, image)

        # pull the image first if not exist
        if not self.image_exists(image):
            self.pull_image(image)

        return self.run_container(
            name, image, env, port_bindings, volumes, dns,
            dns_search, ulimits,
        )

    def get_container_ip(self, container_id):
        """Gets container IP.

        :param container_id: ID or name of the container.
        :returns: Container's IP address.
        """
        info = self.docker.inspect_container(container_id)
        return info["NetworkSettings"]["IPAddress"]

    def remove_container(self, container_id):
        """Removes container.

        :param container_id: ID or name of the container.
        """
        try:
            return self.docker.remove_container(container_id, force=True)
        except docker.errors.APIError as exc:
            err_code = exc.response.status_code
            if err_code == 404:
                self.logger.warn(
                    "container {!r} does not exist".format(container_id))

    def inspect_container(self, container_id):
        """Inspects given container.

        :param container_id: ID or name of the container.
        """
        return self.docker.inspect_container(container_id)

    def stop_container(self, container_id):  # pragma: no cover
        """Stops given container.
        """
        self.docker.stop(container_id)

    def pull_image(self, image):
        resp = self.docker.pull(repository=image, stream=True)
        output = ""

        while True:
            try:
                output = resp.next()
                self.logger.info(output)
            except StopIteration:
                break

        result = json.loads(output)
        if "errorDetail" in result:
            return False
        return True

    def run_container(self, name, image, env=None, port_bindings=None,
                      volumes=None, dns=None, dns_search=None,
                      ulimits=None):
        """Runs a docker container in detached mode.

        This is a two-steps operation:

        1. Creates container
        2. Starts container

        :param name: A name for the container.
        :param image: The image to run.
        :param env: Environment variables.
        :param port_bindings: Port bindings.
        :param volumes: Mapped volumes.
        :param dns: DNS name servers.
        :param dns_search: DNS search domains.
        :param ulimits: ulimit settings.
        :returns: A string of container ID in long format if container
                  is running successfully, otherwise an empty string.
        """
        env = env or {}
        port_bindings = port_bindings or {}
        volumes = volumes or {}
        dns = dns or []
        dns_search = dns_search or []
        ulimits = ulimits or []

        container = self.docker.create_container(
            image=image,
            name=name,
            detach=True,
            environment=env,
            host_config=self.docker.create_host_config(
                port_bindings=port_bindings,
                binds=volumes,
                dns=dns,
                dns_search=dns_search,
                ulimits=ulimits,
            ),
        )
        container_id = container["Id"]
        self.logger.info("container {!r} has been created".format(name))

        if container_id:
            self.docker.start(container=container_id)
            self.logger.info("container {!r} with ID {!r} "
                             "has been started".format(name, container_id))
        return container_id

    def copy_to_container(self, container, src, dest):
        cfg_str = self._machine_conf_str()
        cmd = "docker {} cp {} {}:{}".format(cfg_str, src, container, dest)
        stdout, stderr, err_code = run_in_shell(cmd)

    # def copy_from_container(self, container, src, dest):
    #     cfg_str = self._machine_conf_str()
    #     cmd = "docker {} cp {}:{} {}".format(cfg_str, container, src, dest)
    #     stdout, stderr, err_code = run_in_shell(cmd)

    def _machine_conf_str(self):
        cfg_str = " ".join([
            "--tlsverify",
            "--tlscacert={}".format(self.machine_conf["tls"].ca_cert),
            "--tlscert={}".format(self.machine_conf["tls"].cert[0]),
            "--tlskey={}".format(self.machine_conf["tls"].cert[1]),
            "-H={}".format(self.machine_conf["base_url"].replace("https", "tcp")),
        ])
        return cfg_str