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
import xml.etree.ElementTree as ET

import pkg_resources

import yardstick.ssh as ssh
from yardstick.benchmark.scenarios import base
import yardstick.common.openstack_utils as op_utils

LOG = logging.getLogger(__name__)


class NumaPinning(base.Scenario):
    """Perform a pinning of virtual machine instances to dedicated NUMA node"""

    __scenario_type__ = "NumaPinning"

    CONTROLLER_SETUP_SCRIPT = "controller_setup.bash"
    COMPUTE_SETUP_SCRIPT = "compute_setup.bash"
    CONTROLLER_RESET_SCRIPT = "controller_reset.bash"
    COMPUTE_RESET_SCRIPT = "compute_reset.bash"

    def __init__(self, scenario_cfg, context_cfg):
        self.scenario_cfg = scenario_cfg
        self.context_cfg = context_cfg
        self.nodes = context_cfg['nodes']
        self.options = scenario_cfg['options']
        self.host_str = self.options.get("host", 'host1')
        self.host_list = self.host_str.split(',')
        self.host_list.sort()
        self.flavor = self.options.get("flavor", 'yardstick-pinned-flavor')
        self.image = self.options.get("image", 'cirros-0.3.3')
        self.external_network = self.options.get("external_network", "ext-net")
        self.cpu_set = self.options.get("cpu_set", '1,2,3,4,5,6')
        self.host_memory = self.options.get("host_memory", 512)
        self.nova_client = op_utils.get_nova_client()
        self.neutron_client = op_utils.get_neutron_client()
        self.glance_client = op_utils.get_glance_client()
        self.instance = None
        self.client = None

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
        self.controller_setup_script = pkg_resources.resource_filename(
            "yardstick.benchmark.scenarios.compute",
            NumaPinning.CONTROLLER_SETUP_SCRIPT)

        self.compute_setup_script = pkg_resources.resource_filename(
            "yardstick.benchmark.scenarios.compute",
            NumaPinning.COMPUTE_SETUP_SCRIPT)

        # log in a contronller node to setup
        self.controller_node_name = self._get_host_node(self.host_list,
                                                        'Controller')
        LOG.debug("The Controller Node is: %s", self.controller_node_name)
        for controller_node in self.controller_node_name:
            self._ssh_host(controller_node)
            # copy script to host
            self.client._put_file_shell(
                self.controller_setup_script, '~/controller_setup.sh')
            # setup controller node
            status, stdout, stderr = self.client.execute(
                "sudo bash controller_setup.sh")
            if status:
                raise RuntimeError(stderr)

        # log in a compute node to setup
        self.compute_node_name = self._get_host_node(self.host_list, 'Compute')
        LOG.debug("The Compute Node is: %s", self.compute_node_name)
        for compute_node in self.compute_node_name:
            self._ssh_host(compute_node)
            # copy script to host
            self.client._put_file_shell(
                self.compute_setup_script, '~/compute_setup.sh')
            # setup compute node
            status, stdout, stderr = self.client.execute(
                "sudo bash compute_setup.sh %s %d" % (self.cpu_set,
                                                      self.host_memory))
            if status:
                raise RuntimeError(stderr)

    def run(self, result):
        """execute the benchmark"""

        network_id = op_utils.get_network_id(self.neutron_client,
                                             self.external_network)
        image_id = op_utils.get_image_id(self.glance_client, self.image)

        LOG.debug("Creating NUMA-pinned-instance-1...")
        self.instance = op_utils.create_instance_and_wait_for_active(
            self.flavor, image_id, network_id,
            instance_name="NUMA-pinned-instance-1")

        cmd = "virsh dumpxml %s" % self.instance.id
        LOG.debug("Executing command: %s", cmd)
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
            self.flavor, image_id, network_id,
            instance_name="NUMA-pinned-instance-2")

        status = op_utils.check_status("ERROR", "NUMA-pinned-instance-2",
                                       10, 5)

        if status:
            print("Create NUMA-pinned-instance-2 failed")

        op_utils.delete_instance(self.nova_client, self.instance.id)
        op_utils.delete_instance(self.nova_client, self.instance_2.id)

    def teardown(self):
        """teardown the benchmark"""

        self.controller_reset_script = pkg_resources.resource_filename(
            "yardstick.benchmark.scenarios.compute",
            NumaPinning.CONTROLLER_RESET_SCRIPT)

        self.compute_reset_script = pkg_resources.resource_filename(
            "yardstick.benchmark.scenarios.compute",
            NumaPinning.COMPUTE_RESET_SCRIPT)

        # log in a compute node to reset
        for compute_node in self.compute_node_name:
            self._ssh_host(compute_node)
            # copy script to host
            self.client._put_file_shell(
                self.compute_reset_script, '~/compute_reset.sh')
            # reset compute node
            status, stdout, stderr = self.client.execute(
                "sudo bash compute_reset.sh")
            if status:
                raise RuntimeError(stderr)

        # log in a contronller node to reset
        for controller_node in self.controller_node_name:
            self._ssh_host(controller_node)
            # copy script to host
            self.client._put_file_shell(
                self.controller_reset_script, '~/controller_reset.sh')
            # reset controller node
            status, stdout, stderr = self.client.execute(
                "sudo bash controller_reset.sh")
            if status:
                raise RuntimeError(stderr)
