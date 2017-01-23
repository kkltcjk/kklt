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


class CpuPinning(base.Scenario):
    """Perform a pinning of virtual machine instances to dedicated physical CPU
    cores.
    """

    __scenario_type__ = "CpuPinning"

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
        self.nova_client = None
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
            CpuPinning.CONTROLLER_SETUP_SCRIPT)

        self.compute_setup_script = pkg_resources.resource_filename(
            "yardstick.benchmark.scenarios.compute",
            CpuPinning.COMPUTE_SETUP_SCRIPT)

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

        self.nova_client = op_utils.get_nova_client()
        self.instance = self.nova_client.servers.create(
            name="cpu-pinned-instance", flavor=self.flavor, image=self.image,
            nics=self.external_network)

        # Check VM status
        op_utils.check_status("ACTIVE", "NUMA-pinned-instance-1", 10, 5)

        cmd = "virsh dumpxml %s" % self.instance.id
        LOG.debug("Executing command: %s", cmd)
        status, stdout, stderr = self.client.execute(cmd)
        if status:
            raise RuntimeError(stderr)

        root = ET.fromstring(stdout)
        for vcpupin in root.iter('vcpupin'):
            result.update(vcpupin.attrib)

    def teardown(self):
        """teardown the benchmark"""

        self.controller_reset_script = pkg_resources.resource_filename(
            "yardstick.benchmark.scenarios.compute",
            CpuPinning.CONTROLLER_RESET_SCRIPT)

        self.compute_reset_script = pkg_resources.resource_filename(
            "yardstick.benchmark.scenarios.compute",
            CpuPinning.COMPUTE_RESET_SCRIPT)

        op_utils.delete_instance(self.nova_client, self.instance.id)

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