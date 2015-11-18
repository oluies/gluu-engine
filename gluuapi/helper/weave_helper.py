# -*- coding: utf-8 -*-
# Copyright (c) 2015 Gluu
#
# All rights reserved.

import logging
import time

from crochet import run_in_reactor

from .salt_helper import SaltHelper
from ..database import db


class WeaveHelper(object):
    def __init__(self, provider, app, logger=None):
        self.provider = provider
        try:
            self.cluster = db.all("clusters")[0]
        except IndexError:
            self.cluster = None

        self.app = app
        self.salt = SaltHelper()
        self.logger = logger or logging.getLogger(
            __name__ + "." + self.__class__.__name__,
        )

    @run_in_reactor
    def launch_async(self, register_minion=True):
        self.launch(register_minion)

    def launch(self, register_minion=True):
        if register_minion:
            self.prepare_minion()

        if self.provider.type == "master":
            self.launch_master()
        else:
            self.launch_consumer()

        # wait for weave to run before exposing its network
        time.sleep(5)
        self.expose_network()

    def prepare_minion(self, connect_delay=10, exec_delay=15):
        """Waits for minion to connect before doing any remote execution.
        """
        # wait for 10 seconds to make sure minion connected
        # and sent its key to master
        # TODO: there must be a way around this
        self.logger.info("Waiting for minion to connect; sleeping for "
                         "{} seconds".format(connect_delay))
        time.sleep(connect_delay)

        # register the container as minion
        self.salt.register_minion(self.provider.hostname)

        # delay the remote execution
        # see https://github.com/saltstack/salt/issues/13561
        # TODO: there must be a way around this
        self.logger.info("Preparing remote execution; sleeping for "
                         "{} seconds".format(exec_delay))
        time.sleep(exec_delay)

    def expose_network(self):
        addr, prefixlen = self.cluster.exposed_weave_ip
        self.logger.info("exposing weave network at {}/{}".format(
            addr, prefixlen
        ))
        self.salt.cmd(
            self.provider.hostname,
            "cmd.run",
            ["weave expose {}/{}".format(addr, prefixlen)],
        )

    def launch_master(self):
        self.logger.info("re-launching weave for master provider")
        stop_cmd = "weave stop"
        self.salt.cmd(self.provider.hostname, "cmd.run", [stop_cmd])
        time.sleep(5)

        ctx = {
            "password": self.cluster.decrypted_admin_pw,
            "ipnet": self.cluster.weave_ip_network,
        }
        launch_cmd = "weave launch-router --password {password} " \
                     "--dns-domain gluu.local " \
                     "--ipalloc-range {ipnet} " \
                     "--ipalloc-default-subnet {ipnet}".format(**ctx)
        self.salt.cmd(self.provider.hostname, "cmd.run", [launch_cmd])

    def launch_consumer(self):
        self.logger.info("re-launching weave for consumer provider")
        stop_cmd = "weave stop"
        self.salt.cmd(self.provider.hostname, "cmd.run", [stop_cmd])
        time.sleep(5)

        ctx = {
            "password": self.cluster.decrypted_admin_pw,
            "ipnet": self.cluster.weave_ip_network,
            "master_ipaddr": self.app.config["SALT_MASTER_IPADDR"],
        }
        launch_cmd = "weave launch-router --password {password} " \
                     "--dns-domain gluu.local " \
                     "--ipalloc-range {ipnet} " \
                     "--ipalloc-default-subnet {ipnet} " \
                     "{master_ipaddr}".format(**ctx)
        self.salt.cmd(self.provider.hostname, "cmd.run", [launch_cmd])

    def attach(self, cidr, node_id):
        attach_cmd = "weave attach {} {}".format(cidr, node_id)
        self.logger.info("attaching weave IP address {}".format(cidr))
        jid = self.salt.cmd_async(
            self.provider.hostname, "cmd.run", [attach_cmd]
        )
        self.salt.subscribe_event(jid, self.provider.hostname)

    def detach(self, cidr, node_id):
        attach_cmd = "weave detach {} {}".format(cidr, node_id)
        self.logger.info("detaching weave IP address {}".format(cidr))
        jid = self.salt.cmd_async(
            self.provider.hostname, "cmd.run", [attach_cmd]
        )
        self.salt.subscribe_event(jid, self.provider.hostname)

    def dns_add(self, node_id, domain_name):
        dns_cmd = "weave dns-add {} -h {}".format(node_id, domain_name)
        self.logger.info("adding {} to local DNS server".format(domain_name))
        jid = self.salt.cmd_async(self.provider.hostname, "cmd.run", [dns_cmd])
        self.salt.subscribe_event(jid, self.provider.hostname)

    def docker_bridge_ip(self):
        jid = self.salt.cmd_async(
            self.provider.hostname, "cmd.run", ["weave docker-bridge-ip"]
        )
        resp = self.salt.subscribe_event(jid, self.provider.hostname)
        return resp["data"]["return"]
