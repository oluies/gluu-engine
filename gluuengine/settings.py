# -*- coding: utf-8 -*-
# Copyright (c) 2015 Gluu
#
# All rights reserved.

import os


class Config(object):
    DEBUG = False
    TESTING = False

    # This directory
    APP_DIR = os.path.abspath(os.path.dirname(__file__))

    HOST = os.environ.get("HOST", "127.0.0.1")
    PORT = os.environ.get("PORT", 8080)

    DATA_DIR = os.environ.get("DATA_DIR", "/var/lib/gluuengine")

    DATABASE_URI = os.environ.get(
        "DATABASE_URI",
        "mongodb://mongo:27017/gluuengine",
    )
    # flask-pymongo compatibility
    MONGO_URI = DATABASE_URI
    SHARED_DATABASE_URI = os.environ.get(
        "SHARED_DATABASE_URI",
        os.path.join(DATA_DIR, "db", "shared.json"),
    )

    TEMPLATES_DIR = os.path.join(APP_DIR, "templates")
    LOG_DIR = os.environ.get("LOG_DIR", "/var/log/gluuengine")
    CONTAINER_LOG_DIR = os.path.join(LOG_DIR, "containers")
    INSTANCE_DIR = os.path.join(DATA_DIR, "instance")

    CUSTOM_LDAP_SCHEMA_DIR = os.path.join(
        DATA_DIR, "custom", "opendj", "schema",
    )
    SSL_CERT_DIR = os.path.join(DATA_DIR, "ssl_certs")

    # container override directories
    OXAUTH_OVERRIDE_DIR = os.path.join(DATA_DIR, "override", "oxauth")
    OXTRUST_OVERRIDE_DIR = os.path.join(DATA_DIR, "override", "oxtrust")
    OXIDP_OVERRIDE_DIR = os.path.join(DATA_DIR, "override", "oxidp")
    #DRIVERS = ['generic','amazonec2','digitalocean', 'google']
    PROVIDER_TYPES = ['generic', 'aws', 'do', 'google']

    # container volume directories
    OPENDJ_VOLUME_DIR = os.path.join(DATA_DIR, "volumes", "opendj")
    OXAUTH_VOLUME_DIR = os.path.join(DATA_DIR, "volumes", "oxauth")
    OXAUTH_MAP_JARS = os.path.join(OXAUTH_VOLUME_DIR, 'jars')
    WEAVE_ENCRYPTION = False

    REGISTRY_CERT_DIR = os.path.join(DATA_DIR, "registry_certs")
    NODE_LOG_PATH = os.path.join(LOG_DIR, "node.log")

    OXAUTH_LOGS_VOLUME_DIR = os.path.join(LOG_DIR, "oxauth")
    OXIDP_LOGS_VOLUME_DIR = os.path.join(LOG_DIR, "oxidp")

    GLUU_IMAGE_TAG = os.environ.get("GLUU_IMAGE_TAG", "latest")
    ENABLE_LICENSE = True

    KEYSTORE_DIR = os.path.join(DATA_DIR, "keystore")


class ProdConfig(Config):
    """Production configuration.
    """


class DevConfig(Config):
    """Development configuration.
    """
    DEBUG = True
    DATABASE_URI = os.environ.get("DATABASE_URI", "mongodb://mongo:27017/gluuengine-dev")
    MONGO_URI = DATABASE_URI
    ENABLE_LICENSE = False


class TestConfig(Config):
    TESTING = True
    DEBUG = True
    DATABASE_URI = os.environ.get("DATABASE_URI", "mongodb://mongo:27017/gluuengine-test")
    MONGO_URI = DATABASE_URI
    ENABLE_LICENSE = False
