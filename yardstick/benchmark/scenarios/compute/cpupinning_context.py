##############################################################################
# Copyright (c) 2017 Huawei Technologies Co.,Ltd and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

from __future__ import print_function
from __future__ import absolute_import

import os
import logging
import xml.etree.ElementTree as ET

import yaml

import yardstick.ssh as ssh
from yardstick.benchmark.scenarios import base
from yardstick.common import constants as consts
import yardstick.common.openstack_utils as op_utils
from yardstick.common.task_template import TaskTemplate

LOG = logging.getLogger(__name__)


class CpuPinning(base.Scenario):
    """Perform a pinning of virtual machine instances to dedicated physical CPU
    cores.
    """

    __scenario_type__ = "CpuPinning-context"

    def __init__(self, scenario_cfg, context_cfg):
        self.scenario_cfg = scenario_cfg
        self.context_cfg = context_cfg
        self.options = self.scenario_cfg['options']
        self.cpu_set = self.options.get("cpu_set", None)
        self.host_str = self.options.get("host", "node4")
        self.host_list = self.host_str.split(',')
        self.nova_client = op_utils.get_nova_client()
        self.instance = None
        self.client = None

        node_file = os.path.join(consts.YARDSTICK_ROOT_PATH,
                                 self.options.get("file"))
        with open(node_file) as f:
            nodes = yaml.safe_load(TaskTemplate.render(f.read()))
        self.nodes = {a['name']: a for a in nodes['nodes']}

        self.setup_done = False

    def _get_host_node(self, hosts, node_type):
        # get node for given node type
        nodes = [a for a in hosts if self.nodes.get(a, {}).get('role') ==
                 node_type]
        if not nodes:
            LOG.error("Can't find %s node in the context!!!", node_type)
        return nodes

    def _ssh_host(self, node_name):
        # ssh host
        node = self.nodes.get(node_name, None)
        user = str(node.get('user', 'ubuntu'))
        ssh_port = str(node.get("ssh_port", ssh.DEFAULT_PORT))
        ip = str(node.get('ip', None))
        pwd = str(node.get('password', None))
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

    def setup(self):
        """scenario setup"""

        # log in a compute node
        self.compute_node_name = self._get_host_node(self.host_list, 'Compute')
        LOG.debug("The Compute Node is: %s", self.compute_node_name)
        for compute_node in self.compute_node_name:
            self._ssh_host(compute_node)

        self.setup_done = True

    def run(self, result):
        """execute the benchmark"""

        if not self.setup_done:
            self.setup()

        host = self.scenario_cfg.get('host')
        self.instance = op_utils.get_instance_by_name(self.nova_client, host)

        cmd = "virsh dumpxml %s" % self.instance.id
        LOG.debug("Dumping VM configrations: %s", cmd)
        status, stdout, stderr = self.client.execute(cmd)
        if status:
            raise RuntimeError(stderr)

        pinning = []
        test_status = 1
        root = ET.fromstring(stdout)
        for vcpupin in root.iter('vcpupin'):
            pinning.append(vcpupin.attrib)

        for item in pinning:
            if str(item["cpuset"]) not in self.cpu_set:
                test_status = 0
                print("Test failed: VM CPU not pinned correctly!")
                break

        print("Test passed: VM CPU pinned correctly!")

        result.update({"Test": test_status})
        result.update({"pinning": pinning})
