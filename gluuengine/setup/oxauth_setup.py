# -*- coding: utf-8 -*-
# Copyright (c) 2015 Gluu
#
# All rights reserved.

import os.path

from blinker import signal

from .base import OxSetup


class OxauthSetup(OxSetup):
    def render_server_xml_template(self):
        """Copies rendered Tomcat's server.xml into the container.
        """
        src = "oxauth/server.xml"
        dest = os.path.join(self.container.tomcat_conf_dir, os.path.basename(src))
        ctx = {
            "shib_jks_pass": self.cluster.decrypted_admin_pw,
            "shib_jks_fn": self.cluster.shib_jks_fn,
        }
        self.copy_rendered_jinja_template(src, dest, ctx)

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

    def setup(self):
        hostname = self.container.hostname

        # render config templates
        self.render_ldap_props_template()
        self.render_server_xml_template()
        self.render_oxauth_context()

        self.write_salt_file()
        self.render_httpd_conf()
        self.configure_vhost()

        self.gen_cert("shibIDP", self.cluster.decrypted_admin_pw,
                      "tomcat", "tomcat", hostname)
        self.get_web_cert()

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

        self.pull_oxauth_override()
        self.pull_java_keystore()
        self.add_auto_startup_entry()
        self.change_cert_access("tomcat", "tomcat")
        self.reload_supervisor()
        return True

    def teardown(self):
        """Teardowns the container.
        """
        complete_sgn = signal("ox_teardown_completed")
        complete_sgn.send(self)

    def after_setup(self):
        """Post-setup callback.
        """
        complete_sgn = signal("ox_setup_completed")
        complete_sgn.send(self)

    def render_httpd_conf(self):
        """Copies rendered Apache2's virtual host into the container.
        """
        src = "oxauth/gluu_httpd.conf"
        file_basename = os.path.basename(src)
        dest = os.path.join("/etc/apache2/sites-available", file_basename)

        ctx = {
            "hostname": self.container.hostname,
            "httpd_cert_fn": "/etc/certs/nginx.crt",
            "httpd_key_fn": "/etc/certs/nginx.key",
        }
        self.copy_rendered_jinja_template(src, dest, ctx)

    def render_oxauth_context(self):
        """Renders oxAuth context file for Tomcat.
        """
        src = "oxauth/oxauth.xml"
        dest = "/opt/tomcat/conf/Catalina/localhost/oxauth.xml"
        ctx = {
            "oxauth_jsf_salt": os.urandom(16).encode("hex"),
        }
        self.copy_rendered_jinja_template(src, dest, ctx)

    def pull_oxauth_override(self):
        src = self.app.config["OXAUTH_OVERRIDE_DIR"]

        if os.path.exists(src):
            dest = "{}:/var/gluu/webapps/oxauth".format(self.node.name)
            self.logger.info("copying {} to {} recursively".format(src, dest))
            self.machine.scp(src, dest, recursive=True)

    # hotfix to copy and distribute jks to oxAuth container
    # TODO: remove this once oxEleven is introduced
    def pull_java_keystore(self):
        if not os.path.exists(self.app.config["KEYSTORE_DIR"]):
            os.makedirs(self.app.config["KEYSTORE_DIR"])

        for jks in ("oxauth-keys.jks", "scim-rp.jks", "scim-rs.jks",):
            # jks in control host
            local_jks = "{}/{}".format(self.app.config["KEYSTORE_DIR"], jks)

            # jks in container
            remote_jks = "/etc/certs/{}".format(jks)

            if not os.path.exists(local_jks):
                try:
                    with self.app.app_context():
                        ldap = self.cluster.get_containers("ldap")[0]
                except IndexError:
                    self.logger.warn("unable to find any ldap container "
                                     "to pull keystores from")
                    return
                else:
                    self.docker.copy_from_container(
                        ldap.cid, remote_jks, local_jks,
                    )

            self.logger.info("pulling {} keystore".format(jks))
            self.docker.copy_to_container(
                self.container.cid, local_jks, remote_jks,
            )
