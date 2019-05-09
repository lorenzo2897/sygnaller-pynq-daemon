#!/usr/bin/env python3

import uuid
import urllib.parse
import urllib.request
import socket

registry_server = 'http://sygnaller.silvestri.io:8000/'


def _query(params):
    url = registry_server + '?' + urllib.parse.urlencode(params)
    resp = urllib.request.urlopen(url).read()
    return resp


def get_mac():
    """Get the MAC address of the default interface"""
    return "%012X" % uuid.getnode()


def get_ip():
    """Get the IP address that routes to the public internet"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip


def register():
    """Register the device with the Pynq boards registry"""
    params = {
        'action': 'register_device',
        'mac': get_mac(),
        'ip': get_ip()
    }
    _query(params)


if __name__ == '__main__':
    register()
