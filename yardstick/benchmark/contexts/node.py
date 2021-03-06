##############################################################################
# Copyright (c) 2015 Huawei Technologies Co.,Ltd and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

from __future__ import absolute_import
import sys
import subprocess
import os
import yaml
import logging
import pkg_resources

from yardstick import ssh
from yardstick.benchmark.contexts.base import Context
from yardstick.definitions import YARDSTICK_ROOT_PATH

LOG = logging.getLogger(__name__)


class NodeContext(Context):
    '''Class that handle nodes info'''

    __context_type__ = "Node"

    def __init__(self):
        self.name = None
        self.file_path = None
        self.nodes = []
        self.controllers = []
        self.computes = []
        self.baremetals = []
        self.env = []
        super(self.__class__, self).__init__()

    def init(self, attrs):
        '''initializes itself from the supplied arguments'''
        self.name = attrs["name"]
        self.file_path = attrs.get("file", "pod.yaml")
        if not os.path.exists(self.file_path):
            self.file_path = os.path.join(YARDSTICK_ROOT_PATH, self.file_path)

        LOG.info("Parsing pod file: %s", self.file_path)

        try:
            with open(self.file_path) as stream:
                cfg = yaml.load(stream)
        except IOError as ioerror:
            sys.exit(ioerror)

        self.nodes.extend(cfg["nodes"])
        self.controllers.extend([node for node in cfg["nodes"]
                                 if node["role"] == "Controller"])
        self.computes.extend([node for node in cfg["nodes"]
                              if node["role"] == "Compute"])
        self.baremetals.extend([node for node in cfg["nodes"]
                                if node["role"] == "Baremetal"])
        LOG.debug("Nodes: %r", self.nodes)
        LOG.debug("Controllers: %r", self.controllers)
        LOG.debug("Computes: %r", self.computes)
        LOG.debug("BareMetals: %r", self.baremetals)

        self.env = attrs.get('env', {})
        LOG.debug("Env: %r", self.env)

    def deploy(self):
        setups = self.env.get('setup', [])
        for setup in setups:
            for host, info in setup.items():
                self._execute_script(host, info)

    def undeploy(self):
        teardowns = self.env.get('teardown', [])
        for teardown in teardowns:
            for host, info in teardown.items():
                self._execute_script(host, info)

    def _get_server(self, attr_name):
        '''lookup server info by name from context
        attr_name: a name for a server listed in nodes config file
        '''
        if type(attr_name) is dict:
            return None

        if self.name != attr_name.split(".")[1]:
            return None
        node_name = attr_name.split(".")[0]
        nodes = [n for n in self.nodes
                 if n["name"] == node_name]
        if len(nodes) == 0:
            return None
        elif len(nodes) > 1:
            LOG.error("Duplicate nodes!!!")
            LOG.error("Nodes: %r", nodes)
            sys.exit(-1)

        # A clone is created in order to avoid affecting the
        # original one.
        node = dict(nodes[0])
        node["name"] = attr_name
        return node

    def _execute_script(self, node_name, info):
        if node_name == 'local':
            self._execute_local_script(info)
        else:
            self._execute_remote_script(node_name, info)

    def _execute_remote_script(self, node_name, info):
        prefix = self.env.get('prefix', '')
        script, options = self._get_script(info)

        script_file = pkg_resources.resource_filename(prefix, script)

        self._get_client(node_name)
        self.client._put_file_shell(script_file, '~/{}'.format(script))

        cmd = 'sudo bash {} {}'.format(script, options)
        status, stdout, stderr = self.client.execute(cmd)
        if status:
            raise RuntimeError(stderr)

    def _execute_local_script(self, info):
        script, options = self._get_script(info)
        script = os.path.join(YARDSTICK_ROOT_PATH, script)
        cmd = 'bash {} {}'.format(script, options)

        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
        LOG.debug('\n%s', p.communicate()[0])

    def _get_script(self, info):
        return info.get('script'), info.get('options')

    def _get_client(self, node_name):
        node = self._get_node_info(node_name)

        user = node.get('user', 'ubuntu')
        ssh_port = node.get("ssh_port", ssh.DEFAULT_PORT)
        ip = node.get('ip', None)
        pwd = node.get('password', None)
        key_fname = node.get('key_filename', '/root/.ssh/id_rsa')

        if pwd is not None:
            LOG.debug("Log in via pw, user:%s, host:%s, password:%s",
                      user, ip, pwd)
            self.client = ssh.SSH(user, ip, password=pwd, port=ssh_port)
        else:
            LOG.debug("Log in via key, user:%s, host:%s, key_filename:%s",
                      user, ip, key_fname)
            self.client = ssh.SSH(user, ip, key_filename=key_fname,
                                  port=ssh_port)

        self.client.wait(timeout=600)

    def _get_node_info(self, node_name):
        for node in self.nodes:
            if node['name'].strip() == node_name.strip():
                return node
        return None
