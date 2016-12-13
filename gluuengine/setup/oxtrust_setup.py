# -*- coding: utf-8 -*-
# Copyright (c) 2015 Gluu
#
# All rights reserved.

import tempfile
import os

from blinker import signal

from .base import OxSetup


class OxtrustSetup(OxSetup):
    def render_check_ssl_template(self):
        """Renders check_ssl script into the container.
        """
        src = self.get_template_path("oxtrust/check_ssl")
        dest = "/usr/bin/{}".format(os.path.basename(src))
        ctx = {"ox_cluster_hostname": self.cluster.ox_cluster_hostname}
        self.render_template(src, dest, ctx)
        self.docker.exec_cmd(self.container.cid, "chmod +x {}".format(dest))

    def setup(self):
        """Runs the actual setup.
        """
        hostname = self.cluster.ox_cluster_hostname.split(":")[0]

        self.render_ldap_props_template()
        self.render_server_xml_template()
        self.write_salt_file()
        self.render_httpd_conf()
        self.configure_vhost()
        self.render_check_ssl_template()

        self.gen_cert("shibIDP", self.cluster.decrypted_admin_pw,
                      "tomcat", "tomcat", hostname)
        self.get_web_cert()

        # IDP keystore
        self.gen_keystore(
            "shibIDP",
            self.cluster.shib_jks_fn,
            self.cluster.decrypted_admin_pw,
            "{}/shibIDP.key".format(self.container.cert_folder),
            "{}/shibIDP.crt".format(self.container.cert_folder),
            "tomcat",
            "tomcat",
            hostname,
        )

        self.pull_oxtrust_override()
        self.add_auto_startup_entry()
        self.change_cert_access("tomcat", "tomcat")
        self.reload_supervisor()
        return True

    def teardown(self):
        """Teardowns the container.
        """
        complete_sgn = signal("ox_teardown_completed")
        complete_sgn.send(self)

    def render_server_xml_template(self):
        """Copies rendered Tomcat's server.xml into the container.
        """
        src = "oxtrust/server.xml"
        dest = os.path.join(self.container.tomcat_conf_dir, os.path.basename(src))
        ctx = {
            "shib_jks_pass": self.cluster.decrypted_admin_pw,
            "shib_jks_fn": self.cluster.shib_jks_fn,
        }
        self.copy_rendered_jinja_template(src, dest, ctx)

    def discover_nginx(self):
        """Discovers nginx container.
        """
        self.logger.debug("discovering available nginx container")
        if self.cluster.count_containers(type_="nginx"):
            self.import_nginx_cert()

    def after_setup(self):
        """Post-setup callback.
        """
        self.push_shib_certkey()
        self.discover_nginx()
        complete_sgn = signal("ox_setup_completed")
        complete_sgn.send(self)

    def add_auto_startup_entry(self):
        """Adds supervisor program for auto-startup.
        """
        self.logger.debug("adding tomcat config for supervisord")
        src = "_shared/tomcat.conf"
        dest = "/etc/supervisor/conf.d/tomcat.conf"
        self.copy_rendered_jinja_template(src, dest)

        self.logger.debug("adding httpd config for supervisord")
        src = "_shared/httpd.conf"
        dest = "/etc/supervisor/conf.d/httpd.conf"
        self.copy_rendered_jinja_template(src, dest)

    def restart_tomcat(self):
        """Restarts Tomcat via supervisorctl.
        """
        self.logger.debug("restarting tomcat")
        restart_cmd = "supervisorctl restart tomcat"
        self.docker.exec_cmd(self.container.cid, restart_cmd)

    def push_shib_certkey(self):
        _, crt = tempfile.mkstemp()
        self.docker.copy_from_container(
            self.container.cid, "/etc/certs/shibIDP.crt", crt,
        )
        _, key = tempfile.mkstemp()
        self.docker.copy_from_container(
            self.container.cid, "/etc/certs/shibIDP.key", key,
        )

        for oxidp in self.cluster.get_containers(type_="oxidp"):
            self.docker.copy_to_container(
                oxidp.cid, crt, "/etc/certs/shibIDP.crt",
            )
            self.docker.copy_to_container(
                oxidp.cid, key, "/etc/certs/shibIDP.key",
            )

        for fn in (crt, key,):
            try:
                os.unlink(fn)
            except OSError:
                pass

    def pull_oxtrust_override(self):
        src = self.app.config["OXTRUST_OVERRIDE_DIR"]

        if os.path.exists(src):
            dest = "{}:/var/gluu/webapps/oxtrust".format(self.node.name)
            self.logger.info("copying {} to {} recursively".format(src, dest))
            self.machine.scp(src, dest, recursive=True)

    def render_httpd_conf(self):
        """Copies rendered Apache2's virtual host into the container.
        """
        src = "oxtrust/gluu_httpd.conf"
        file_basename = os.path.basename(src)
        dest = os.path.join("/etc/apache2/sites-available", file_basename)

        ctx = {
            "hostname": self.container.hostname,
            "httpd_cert_fn": "/etc/certs/nginx.crt",
            "httpd_key_fn": "/etc/certs/nginx.key",
        }
        self.copy_rendered_jinja_template(src, dest, ctx)
