"""LAB E - planted findings for the SAST gate (Gate 3). Never deployed anywhere."""
import os
import subprocess

import yaml


def ping(host):
    # command injection: user input concatenated into a shell command
    os.system("ping -c 1 " + host)


def load_settings(data):
    # unsafe deserialisation: yaml.load without a safe Loader
    return yaml.load(data)


def run(cmd):
    # shell=True with caller-controlled input
    return subprocess.call(cmd, shell=True)
