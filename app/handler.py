"""LAB E - the SAST findings from the red run, remediated. Never deployed anywhere."""
import ipaddress
import subprocess

import yaml


def ping(host):
    # validate input, then pass an argument list: no shell, no string concatenation
    ipaddress.ip_address(host)
    return subprocess.run(["ping", "-c", "1", host], check=False)


def load_settings(data):
    # safe_load builds only plain Python types
    return yaml.safe_load(data)


def run(args):
    # an explicit argument list, shell=False (the default)
    return subprocess.run(list(args), check=False)
