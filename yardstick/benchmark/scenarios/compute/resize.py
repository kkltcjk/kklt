# ############################################################################
# Copyright (c) 2017 Huawei Technologies Co.,Ltd and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
# ############################################################################

from __future__ import print_function
from __future__ import absolute_import

import logging
import os
from datetime import datetime
from xml.etree import ElementTree as ET

import yaml
import pkg_resources

from yardstick import ssh
from yardstick.common import openstack_utils
from yardstick.common import constants as consts
from yardstick.common.task_template import TaskTemplate
from yardstick.benchmark.scenarios import base

LOG = logging.getLogger(__name__)


class Resize(base.Scenario):
    """
    Execute a cold migration for two hosts

    """

    __scenario_type__ = "Resize"

    CONTROLLER_SETUP_SCRIPT = "controller_setup.bash"
    COMPUTE_SETUP_SCRIPT = "compute_setup.bash"
    CONTROLLER_RESET_SCRIPT = "controller_reset.bash"
    COMPUTE_RESET_SCRIPT = "compute_reset.bash"

    def __init__(self, scenario_cfg, context_cfg):
        self.scenario_cfg = scenario_cfg
        self.context_cfg = context_cfg

        host = self.context_cfg['host']
        self.user = host.get('user', 'ubuntu')
        self.port = host.get("ssh_port", ssh.DEFAULT_PORT)
        self.ip = host.get('ip')
        self.key_filename = host.get('key_filename', '/root/.ssh/id_rsa')
        self.password = host.get('password')

        self.options = scenario_cfg['options']
        self.host_str = self.options.get("host", 'host1')
        self.host_list = self.host_str.split(',')
        self.host_list.sort()
        self.cpu_set = self.options.get("cpu_set", '1,2,3,4,5,6')
        self.host_memory = self.options.get("host_memory", 512)

        self.nova_client = openstack_utils.get_nova_client()
        self.neutron_client = openstack_utils.get_neutron_client()
        self.glance_client = openstack_utils.get_glance_client()

        node_file = os.path.join(consts.YARDSTICK_ROOT_PATH,
                                 scenario_cfg.get('node_file'))
        with open(node_file) as f:
            nodes = yaml.safe_load(TaskTemplate.render(f.read()))
        self.nodes = {a['name']: a for a in nodes['nodes']}

    def _get_host_node(self, hosts, type):
        # get node for given node type
        nodes = [a for a in hosts if self.nodes.get(a, {}).get('role') == type]

        if not nodes:
            LOG.error("Can't find %s node in the context!!!", type)

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

    def _get_ssh_client(self):

        if self.password is not None:
            LOG.info("Log in via pw, user:%s, host:%s, pw:%s",
                     self.user, self.ip, self.password)
            self.connection = ssh.SSH(self.user, self.ip,
                                      password=self.password,
                                      port=self.port)
        else:
            LOG.info("Log in via key, user:%s, host:%s, key_filename:%s",
                     self.user, self.ip, self.key_filename)
            self.connection = ssh.SSH(self.user, self.ip,
                                      key_filename=self.key_filename,
                                      port=self.port)

        self.connection.wait(timeout=600)

    def mysetup(self):
        """scenario setup"""
        self.controller_setup_script = pkg_resources.resource_filename(
            "yardstick.benchmark.scenarios.compute",
            Resize.CONTROLLER_SETUP_SCRIPT)

        self.compute_setup_script = pkg_resources.resource_filename(
            "yardstick.benchmark.scenarios.compute",
            Resize.COMPUTE_SETUP_SCRIPT)

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

    def _write_remote_file(self):
        self._get_ssh_client()
        cmd = "echo 'Hello World!' > resize.data"
        self.connection.execute(cmd)

    def _check_file_content(self):
        self._get_ssh_client()
        cmd = 'cat resize.data'
        status, stdout, stderr = self.connection.execute(cmd)
        print(stdout.strip())

    def run(self, result):

        self._write_remote_file()

        server_name = self.scenario_cfg['host']
        new_flavor_name = self.scenario_cfg['vm1_new_flavor']
        duration = self._do_resize(server_name, new_flavor_name)
        print('The duration is {}'.format(duration))

        self._check_file_content()

        self.mysetup()
        vm2_server_name = '{}-2'.format(server_name)
        vm2_image_name = self.scenario_cfg['vm2_image']
        vm2_origin_flavor_name = self.scenario_cfg['vm2_origin_flavor']
        vm2_new_flavor_name = self.scenario_cfg['vm2_new_flavor']

        network_id = openstack_utils.get_network_id(self.neutron_client,
                                                    'ext-net')
        image_id = openstack_utils.get_image_id(self.glance_client,
                                                vm2_image_name)

        self.instance = openstack_utils.create_instance_and_wait_for_active(
            vm2_origin_flavor_name, image_id, network_id,
            instance_name=vm2_server_name)

        data = self._check_numa_node(self.instance.id)
        print(data)

        duration = self._do_resize(vm2_server_name, vm2_new_flavor_name)

        data = self._check_numa_node(self.instance.id)
        print(data)

        print('The duration is {}'.format(duration))
        self.myteardown()

    def _check_numa_node(self, server_id):
        for compute_node in self.compute_node_name:
            print(compute_node)
            self._ssh_host(compute_node)

        cmd = "virsh dumpxml %s" % server_id
        LOG.debug("Executing command: %s", cmd)
        status, stdout, stderr = self.client.execute(cmd)
        if status:
            raise RuntimeError(stderr)
        pinning = []
        root = ET.fromstring(stdout)
        for memnode in root.iter('memnode'):
            pinning.append(memnode.attrib)
        return {"pinning": pinning}

    def _do_resize(self, server_name, new_flavor_name):
        nova_client = openstack_utils.get_nova_client()

        server_id = openstack_utils.get_server_by_name(server_name).id
        new_flavor = openstack_utils.get_flavor_by_name(new_flavor_name)

        t1 = datetime.now()
        nova_client.servers.resize(server_id, new_flavor)
        openstack_utils.check_status('VERIFY_RESIZE', server_name, 100, 1)
        nova_client.servers.confirm_resize(server_id)
        t2 = datetime.now()
        duration = (t2 - t1).seconds

        return duration

    def myteardown(self):
        """teardown the benchmark"""

        self.controller_reset_script = pkg_resources.resource_filename(
            "yardstick.benchmark.scenarios.compute",
            Resize.CONTROLLER_RESET_SCRIPT)

        self.compute_reset_script = pkg_resources.resource_filename(
            "yardstick.benchmark.scenarios.compute",
            Resize.COMPUTE_RESET_SCRIPT)

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
