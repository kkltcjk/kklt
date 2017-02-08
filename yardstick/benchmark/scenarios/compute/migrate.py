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
import subprocess

import yaml
import pkg_resources

from yardstick import ssh
from yardstick.common import openstack_utils
from yardstick.common import constants as consts
from yardstick.common.task_template import TaskTemplate
from yardstick.benchmark.scenarios import base

LOG = logging.getLogger(__name__)


class Migrate(base.Scenario):
    """
    Execute a live migration for two hosts

    """

    __scenario_type__ = "Migrate"

    CONTROLLER_SETUP = 'migrate_controller_setup.bash'
    CONTROLLER_TEARDOWN = 'migrate_controller_teardown.bash'
    COMPUTE_SERVER_SETUP = 'migrate_compute_server_setup.bash'
    COMPUTE_SERVER_TEARDOWN = 'migrate_compute_server_teardown.bash'
    COMPUTE_CLIENT_SETUP = 'migrate_compute_client_setup.bash'
    COMPUTE_CLIENT_TEARDOWN = 'migrate_compute_client_teardown.bash'

    PRE_PATH = "yardstick.benchmark.scenarios.compute"

    def __init__(self, scenario_cfg, context_cfg):
        self.scenario_cfg = scenario_cfg
        self.context_cfg = context_cfg
        print(self.scenario_cfg)
        print(self.context_cfg)

        host = self.context_cfg['host']
        self.user = host.get('user', 'ubuntu')
        self.port = host.get("ssh_port", ssh.DEFAULT_PORT)
        self.ip = host.get('ip')
        self.key_filename = host.get('key_filename', '/root/.ssh/id_rsa')
        self.password = host.get('password')

        options = scenario_cfg['options']
        self.host_list = options.get('host').split(',')
        self.cpu_set = options.get("cpu_set", '1,2,3,4,5,6')
        self.host_memory = options.get("host_memory", 512)

        print(self.host_list)

        self.nova_client = openstack_utils.get_nova_client()
        self.neutron_client = openstack_utils.get_neutron_client()
        self.glance_client = openstack_utils.get_glance_client()

        node_file = os.path.join(consts.YARDSTICK_ROOT_PATH,
                                 scenario_cfg.get('node_file'))
        with open(node_file) as f:
            nodes = yaml.safe_load(TaskTemplate.render(f.read()))
        self.nodes = {a['name']: a for a in nodes['nodes']}
        print(self.nodes)

    def _get_hosts(self, hosts, type):
        # get node for given node type
        nodes = [a for a in hosts if self.nodes.get(a, {}).get('role') == type]

        if not nodes:
            LOG.error("Can't find %s node in the context!!!", type)

        return nodes

    def _get_host_client(self, node_name):
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
            self.host_client = ssh.SSH(user, ip, password=pwd, port=ssh_port)
        else:
            LOG.debug("Log in via key, user:%s, host:%s, key_filename:%s",
                      user, ip, key_fname)
            self.host_client = ssh.SSH(user, ip, key_filename=key_fname,
                                       port=ssh_port)

        self.host_client.wait(timeout=600)

    def _get_instance_client(self):

        if self.password is not None:
            LOG.info("Log in via pw, user:%s, host:%s, pw:%s",
                     self.user, self.ip, self.password)
            self.instance_client = ssh.SSH(self.user, self.ip,
                                           password=self.password,
                                           port=self.port)
        else:
            LOG.info("Log in via key, user:%s, host:%s, key_filename:%s",
                     self.user, self.ip, self.key_filename)
            self.instance_client = ssh.SSH(self.user, self.ip,
                                           key_filename=self.key_filename,
                                           port=self.port)

        self.instance_client.wait(timeout=600)

    def _execute_script(self, node, script, options=''):
        script_file = pkg_resources.resource_filename(Migrate.PRE_PATH, script)

        self._get_host_client(node)
        self.host_client._put_file_shell(script_file, '~/{}'.format(script))

        cmd = 'sudo bash {}{}'.format(script, options)
        status, stdout, stderr = self.host_client.execute(cmd)
        if status:
            raise RuntimeError(stderr)

    def mysetup(self):
        controller_nodes = self._get_hosts(self.host_list, 'Controller')
        LOG.debug("The Controller Node is: %s", controller_nodes)
        for node in controller_nodes:
            self._execute_script(node, Migrate.CONTROLLER_SETUP)

        compute_nodes = self._get_hosts(self.host_list, 'Compute')
        LOG.debug("The Compute Node is: %s", compute_nodes)

        options = ' {} {}'.format(self.cpu_set, self.host_memory)
        self._execute_script(compute_nodes[0], Migrate.COMPUTE_SERVER_SETUP,
                             options)

        for node in compute_nodes[1:]:
            self._execute_script(node, Migrate.COMPUTE_CLIENT_SETUP, options)

    def run(self, result):
        self.mysetup()

        vm3_server_name = '{}-3'.format(self.scenario_cfg['host'])
        flavor = self.scenario_cfg.get('flavor')
        image = self.scenario_cfg.get('image')
        net = self.scenario_cfg.get('network')

        network_id = openstack_utils.get_network_id(self.neutron_client, net)
        image_id = openstack_utils.get_image_id(self.glance_client, image)

        self.instance = openstack_utils.create_instance_and_wait_for_active(
            flavor, image_id, network_id, instance_name=vm3_server_name)

        print(vars(self.instance))

        host = 'host5'
        cmd = ['nova', 'live-migration', self.instance.id, host]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        print(p.communicate()[0])

        self.myteardown()

    def myteardown(self):
        controller_nodes = self._get_hosts(self.host_list, 'Controller')
        LOG.debug("The Controller Node is: %s", controller_nodes)
        for node in controller_nodes:
            self._execute_script(node, Migrate.CONTROLLER_TEARDOWN)

        compute_nodes = self._get_hosts(self.host_list, 'Compute')
        LOG.debug("The Compute Node is: %s", compute_nodes)

        for node in compute_nodes[1:]:
            self._execute_script(node, Migrate.COMPUTE_CLIENT_TEARDOWN)

        self._execute_script(compute_nodes[0], Migrate.COMPUTE_SERVER_TEARDOWN)
