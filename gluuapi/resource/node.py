# -*- coding: utf-8 -*-
# The MIT License (MIT)
#
# Copyright (c) 2015 Gluu
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
from flask import current_app
from flask.ext.restful import Resource
from flask_restful_swagger import swagger

from gluuapi.database import db
from gluuapi.reqparser import node_req

from gluuapi.helper import DockerHelper
from gluuapi.helper import SaltHelper
from gluuapi.helper import LdapModelHelper
from gluuapi.helper import OxauthModelHelper
from gluuapi.helper import OxtrustModelHelper
from gluuapi.helper import HttpdModelHelper

from gluuapi.setup import LdapSetup
from gluuapi.setup import HttpdSetup


class Node(Resource):
    @swagger.operation(
        notes='Gives a node info/state',
        nickname='getnode',
        parameters=[],
        responseMessages=[
            {
              "code": 200,
              "message": "Node information",
            },
            {
                "code": 404,
                "message": "Node not found",
            },
            {
                "code": 500,
                "message": "Internal Server Error"
            },
        ],
        summary='TODO'
    )
    def get(self, node_id):
        obj = db.get(node_id, "nodes")
        if not obj:
            return {"code": 404, "message": "Node not found"}, 404
        return obj.as_dict()

    @swagger.operation(
        notes='delete a node',
        nickname='delnode',
        parameters=[],
        responseMessages=[
            {
              "code": 204,
              "message": "Node deleted",
            },
            {
                "code": 404,
                "message": "Node not found",
            },
            {
                "code": 500,
                "message": "Internal Server Error",
            },
        ],
        summary='TODO'
    )
    def delete(self, node_id):
        node = db.get(node_id, "nodes")

        if not node:
            return {"code": 404, "message": "Node not found"}, 404

        cluster = db.get(node.cluster_id, "clusters")
        provider = db.get(node.provider_id, "providers")

        docker = DockerHelper(base_url=provider.docker_base_url)
        salt = SaltHelper()

        # remove container
        docker.remove_container(node.id)

        # unregister minion
        salt.unregister_minion(node.id)

        # remove node
        db.delete(node_id, "nodes")

        # removes reference from cluster, if any
        cluster.remove_node(node)
        cluster.unreserve_ip_addr(node.weave_ip)
        db.update(cluster.id, cluster, "clusters")

        if node.type == "ldap":
            setup_obj = LdapSetup(node, cluster)
            setup_obj.teardown()
        elif node.type == "httpd":
            setup_obj = HttpdSetup(node, cluster)
            setup_obj.teardown()
        return {}, 204


class NodeList(Resource):
    @swagger.operation(
        notes='Gives node list info/state',
        nickname='listnode',
        parameters=[],
        responseMessages=[
            {
              "code": 200,
              "message": "List node information",
            },
            {
                "code": 500,
                "message": "Internal Server Error"
            },
        ],
        summary='TODO'
    )
    def get(self):
        obj_list = db.all("nodes")
        return [item.as_dict() for item in obj_list]

    @swagger.operation(
        notes="""This API will create a new Gluu Server cluster node. This may take a while, so the process
is handled asyncronously by the Twisted reactor. It includes creating a new docker instance, deploying
the necessary software components, and updating the configuration of the target node and any
other dependent cluster nodes. Subsequent GET requests will be necessary to find out when the
status of the cluster node is available.""",
        nickname='postnode',
        parameters=[
            {
                "name": "cluster_id",
                "description": "The ID of the cluster",
                "required": True,
                "dataType": "string",
                "paramType": "form",
            },
            {
                "name": "node_type",
                "description": "one of 'ldap', 'oxauth', 'oxtrust', or 'httpd'",
                "required": True,
                "dataType": "string",
                "paramType": "form",
            },
            {
                "name": "provider_id",
                "description": "The ID of the provider",
                "required": True,
                "dataType": "string",
                "paramType": "form",
            },
        ],
        responseMessages=[
            {
                "code": 202,
                "message": "Accepted",
            },
            {
                "code": 400,
                "message": "Bad Request",
            },
            {
                "code": 403,
                "message": "Forbidden",
            },
            {
                "code": 500,
                "message": "Internal Server Error",
            }
        ],
        summary='TODO'
    )
    def post(self):
        params = node_req.parse_args()
        salt_master_ipaddr = current_app.config["SALT_MASTER_IPADDR"]

        cluster = db.get(params.cluster_id, "clusters")
        if not cluster:
            return {"code": 400, "message": "invalid cluster ID"}, 400

        if not cluster.ip_addr_available:
            return {"code": 403, "message": "running out of weave IP"}, 403

        # check that provider ID is valid else return with message and code
        provider = db.get(params.provider_id, "providers")
        if not provider:
            return {"code": 400, "message": "invalid provider ID"}, 400

        if params.node_type == "ldap":
            # checks if this new node will exceed max. allowed LDAP nodes
            if len(cluster.ldap_nodes) + 1 > cluster.max_allowed_ldap_nodes:
                return {"code": 403, "message": "max. allowed LDAP nodes is reached"}, 403
            helper_class = LdapModelHelper
        elif params.node_type == "oxauth":
            helper_class = OxauthModelHelper
        elif params.node_type == "oxtrust":
            helper_class = OxtrustModelHelper
        elif params.node_type == "httpd":
            helper_class = HttpdModelHelper

        helper = helper_class(cluster, provider, salt_master_ipaddr)
        helper.setup()

        print "build logpath: %s" % helper.logpath
        return {}, 202