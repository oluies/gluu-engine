# -*- coding: utf-8 -*-
# Copyright (c) 2015 Gluu
#
# All rights reserved.

import base64
import hashlib
import json
import os
import random
import string
import subprocess
import sys
import traceback
import time
import uuid
from subprocess import CalledProcessError

import requests
from M2Crypto.EVP import Cipher

# Default charset
_DEFAULT_CHARS = "".join([string.ascii_uppercase,
                          string.digits,
                          string.lowercase])


def run(command, exit_on_error=True, cwd=None):
    try:
        return subprocess.check_output(command, stderr=subprocess.STDOUT,
                                       shell=True, cwd=cwd)
    except subprocess.CalledProcessError, e:
        if exit_on_error:
            sys.exit(e.returncode)
        else:
            raise


def get_random_chars(size=12, chars=_DEFAULT_CHARS):
    """Generates random characters.
    """
    return ''.join(random.choice(chars) for _ in range(size))


def ldap_encode(password):
    # borrowed from community-edition-setup project
    # see http://git.io/vIRex
    salt = os.urandom(4)
    sha = hashlib.sha1(password)
    sha.update(salt)
    b64encoded = '{0}{1}'.format(sha.digest(), salt).encode('base64').strip()
    encrypted_password = '{{SSHA}}{0}'.format(b64encoded)
    return encrypted_password


def get_quad():
    # borrowed from community-edition-setup project
    # see http://git.io/he1p
    return str(uuid.uuid4())[:4].upper()


def generate_passkey():
    return "".join([get_random_chars(), get_random_chars()])


def encrypt_text(text, key):
    # Porting from pyDes-based encryption (see http://git.io/htxa)
    # to use M2Crypto instead (see https://gist.github.com/mrluanma/917014)
    cipher = Cipher(alg="des_ede3_ecb", key=b"{}".format(key), op=1, iv="\0" * 16)
    encrypted_text = cipher.update(b"{}".format(text))
    encrypted_text += cipher.final()
    return base64.b64encode(encrypted_text)


def decrypt_text(encrypted_text, key):
    # Porting from pyDes-based encryption (see http://git.io/htpk)
    # to use M2Crypto instead (see https://gist.github.com/mrluanma/917014)
    cipher = Cipher(alg="des_ede3_ecb", key=b"{}".format(key), op=0, iv="\0" * 16)
    decrypted_text = cipher.update(base64.b64decode(b"{}".format(encrypted_text)))
    decrypted_text += cipher.final()
    return decrypted_text


def exc_traceback():
    """Get exception traceback as string.
    """
    exc_info = sys.exc_info()
    exc_string = ''.join(
        traceback.format_exception_only(*exc_info[:2]) +
        traceback.format_exception(*exc_info))
    return exc_string


def decode_signed_license(signed_license, public_key, public_password, license_password):
    """Gets license's metadata from a signed license retrieved from license
    server (https://license.gluu.org).

    :param signed_license: Signed license retrieved from license server
    :param public_key: Public key retrieved from license server
    :param public_password: Public password retrieved from license server
    :param license_password: License password retrieved from license server
    """
    validator = os.environ.get(
        "OXD_LICENSE_VALIDATOR",
        "/usr/share/oxd-license-validator/oxd-license-validator.jar",
    )

    try:
        cmd_output = run("java -jar {} {} {} {} {}".format(
            validator,
            signed_license,
            public_key,
            public_password,
            license_password,
        ), exit_on_error=False)
    except CalledProcessError as exc:  # pragma: no cover
        cmd_output = exc.output

    # output example:
    #
    #   Validator expects: java org.xdi.oxd.license.validator.LicenseValidator
    #   {"valid":true,"metadata":{}}
    #
    # but we only care about the last line
    meta = cmd_output.splitlines()[-1]

    try:
        decoded_license = json.loads(meta)
        return decoded_license
    except ValueError:
        # validator may throws exception as the output,
        # which is not a valid JSON
        raise ValueError("Error parsing JSON output of {}".format(validator))


def retrieve_signed_license(code):
    """Retrieves signed license from https://license.gluu.org.

    :param code: Code (or licenseId).
    """
    resp = requests.post(
        "https://license.gluu.org/oxLicense/rest/generate",
        data={"licenseId": code},
    )
    return resp


def timestamp_millis():
    """Time in milliseconds since the EPOCH.
    """
    return time.time() * 1000
