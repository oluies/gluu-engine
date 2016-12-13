# -*- coding: utf-8 -*-
# Copyright (c) 2015 Gluu
#
# All rights reserved.

from marshmallow import post_load
from marshmallow import validates
from marshmallow import ValidationError

from ..database import db
from ..extensions import ma


class ContainerReq(ma.Schema):
    node_id = ma.Str(required=True)

    @validates("node_id")
    def validate_node(self, value):
        """Validates node's ID.

        :param value: ID of the node.
        """
        node = db.get(value, "nodes")
        self.context["node"] = node

        if not node:
            raise ValidationError("invalid node ID")

        if node.type not in ("master", "worker",):
            raise ValidationError("cannot use non master or worker node")

        if node.type == "worker" and self.context["enable_license"]:
            try:
                license_key = db.all("license_keys")[0]
            except IndexError:
                raise ValidationError("cannot deploy container to worker node "
                                      "due to missing license")

            if license_key.expired:
                raise ValidationError("cannot deploy container to "
                                      "node with expired license")

            if license_key.mismatched:
                raise ValidationError("cannot deploy container to "
                                      "node with incorrect product license")

            if not license_key.is_active:
                raise ValidationError("cannot deploy container to "
                                      "node with non-active license")

    @post_load
    def finalize_data(self, data):
        """Build finalized data.
        """
        data["context"] = self.context
        data["container_attrs"] = {}
        return data
