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


class NumaPinning(base.Scenario):
    """Perform a pinning of virtual machine instances to dedicated NUMA node"""

    __scenario_type__ = "NumaPinning-context"

    CONTROLLER_SETUP_SCRIPT = "controller_setup.bash"
    COMPUTE_SETUP_SCRIPT = "compute_setup.bash"
    CONTROLLER_RESET_SCRIPT = "controller_reset.bash"
    COMPUTE_RESET_SCRIPT = "compute_reset.bash"

    def __init__(self, scenario_cfg, context_cfg):
        self.scenario_cfg = scenario_cfg
        self.context_cfg = context_cfg
        self.options = self.scenario_cfg['options']
        self.host_str = self.options.get("host", "node4")
        self.host_list = self.host_str.split(',')
        self.image = self.options.get("image", 'cirros-0.3.3')
        self.external_network = os.getenv("EXTERNAL_NETWORK")
        self.nova_client = op_utils.get_nova_client()
        self.neutron_client = op_utils.get_neutron_client()
        self.glance_client = op_utils.get_glance_client()
        self.instance = None
        self.instance_2 = None
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

        network_id = op_utils.get_network_id(self.neutron_client,
                                             self.external_network)
        image_id = op_utils.get_image_id(self.glance_client, self.image)

        host = self.scenario_cfg.get('host')
        self.instance = op_utils.get_instance_by_name(self.nova_client, host)

        cmd = "virsh dumpxml %s" % self.instance.id
        LOG.debug("Dumping VM configrations: %s", cmd)
        status, stdout, stderr = self.client.execute(cmd)
        if status:
            raise RuntimeError(stderr)

        pinning = []
        root = ET.fromstring(stdout)
        for memnode in root.iter('memnode'):
            pinning.append(memnode.attrib)

        result.update({"pinning": pinning})

        # Create multiple VMs to test CPU ran out
        LOG.debug("Creating NUMA-pinned-instance-2...")
        self.instance_2 = op_utils.create_instance(
            "yardstick-pinned-flavor", image_id, network_id,
            instance_name="NUMA-pinned-instance-2")

        status = op_utils.check_status("ERROR", "NUMA-pinned-instance-2",
                                       10, 5)

        if status:
            print("Create NUMA-pinned-instance-2 failed: lack of resources.")

        if len(pinning) == 1 and status:
            result.update({"Test": 1})
            print("Test passed!")
        else:
            result.update({"Test": 0})
            print("Test failed!")

        op_utils.delete_instance(self.nova_client, self.instance_2.id)
