##############################################################################
# Copyright (c) 2017 Huawei Technologies Co.,Ltd and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

from __future__ import absolute_import

import logging
import subprocess
from yardstick.common import constants as config

import yardstick.ssh as ssh
from yardstick.benchmark.scenarios import base

LOG = logging.getLogger(__name__)


class Heataction(base.Scenario):
    """Perform a hugepages test.
    """

    __scenario_type__ = "Heataction"

    HEATACTION_CHECK_SCRIPT = "heataction_check.bash"

    def __init__(self, scenario_cfg, context_cfg):
        pass

    def _get_host_node(self, host_list, node_type):
        # get node for given node type
        host_node = []
        for host_name in host_list:
            node = self.nodes.get(host_name, None)
            node_role = node.get('role', None)
            if node_role == node_type:
                host_node.append(host_name)

        if len(host_node) == 0:
            LOG.exception("Can't find %s node in the context!!!", node_type)

        return host_node

    def _ssh_host(self, node_name):
        # ssh host
        node = self.nodes.get(node_name, None)
        user = node.get('user', 'ubuntu')
        ssh_port = node.get("ssh_port", ssh.DEFAULT_PORT)
        ip = node.get('ip', None)
        pwd = node.get('password', None)
        key_fname = node.get('key_filename', '/root/.ssh/id_rsa')

        if pwd is not None:
            LOG.debug("Log via pw, user:%s, host:%s, password:%s",
                      user, ip, pwd)
            self.client = ssh.SSH(user, ip, password=pwd, port=ssh_port)
        else:
            LOG.debug("Log via key, user:%s, host:%s, key_filename:%s",
                      user, ip, key_fname)
            self.client = ssh.SSH(user, ip, key_filename=key_fname,
                                  port=ssh_port)

        self.client.wait(timeout=600)

    def run(self, result):
        """execute the benchmark"""
        vm1_image = self._fetch_diff('heataction-vm1')
        vm2_image = self._fetch_diff('heataction-vm2')
        LOG.debug("vm1 image name: %s, vm2 image name: %s",
                  vm1_image, vm2_image)
        result.update({'test': self._pof(vm1_image != vm2_image)})

    def _fetch_diff(self, name):
        """fetch diff feature of two template"""
        HEATACTION_CHECK_PATH = \
            'yardstick/benchmark/scenarios/compute/heataction-check.bash'
        cmd = ['bash', HEATACTION_CHECK_PATH, name]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                             cwd=config.YARDSTICK_REPOS_DIR)
        return p.communicate()[0]

    def _pof(self, condition):
        """Pass or FAIL helper"""

        return 1 if condition else 0

    def teardown(self):
        """teardown the benchmark"""
        pass
