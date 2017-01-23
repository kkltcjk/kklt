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
from datetime import datetime

from yardstick import ssh
from yardstick.common import openstack_utils
from yardstick.benchmark.scenarios import base

LOG = logging.getLogger(__name__)


class Resize(base.Scenario):
    """
    Execute ping between two hosts

    """

    __scenario_type__ = "Resize"

    def __init__(self, scenario_cfg, context_cfg):
        self.scenario_cfg = scenario_cfg
        self.context_cfg = context_cfg

        host = self.context_cfg['host']
        self.user = host.get('user', 'ubuntu')
        self.port = host.get("ssh_port", ssh.DEFAULT_PORT)
        self.ip = host.get('ip')
        self.key = host.get('key_filename', '/root/.ssh/id_rsa')
        self.password = host.get('password')

    def _get_ssh_client(self):

        if self.password is not None:
            LOG.info("Log in via pw, user:%s, host:%s, pw:%s",
                     self.user, self.ip, self.password)
            self.client = ssh.SSH(self.user, self.ip, password=self.password,
                                  port=self.port)
        else:
            LOG.info("Log in via key, user:%s, host:%s, key_filename:%s",
                     self.user, self.ip, self.key)
            self.client = ssh.SSH(self.user, self.ip, key_filename=self.key,
                                  port=self.port)

        self.client.wait(timeout=600)

    def run(self, result):

        self._write_remote_file()

        server_name = self.scenario_cfg['host']
        new_flavor_name = self.scenario_cfg['vm1_new_flavor']
        duration = self._do_resize(server_name, new_flavor_name)
        print('The duration is {}'.format(duration))

        self._check_file_content()

        vm2_server_name = '{}-2'.format(server_name)
        vm2_image_name = self.scenario_cfg['vm2_image']
        vm2_origin_flavor_name = self.scenario_cfg['vm2_origin_flavor']
        vm2_new_flavor_name = self.scenario_cfg['vm2_new_flavor']
        self._create_server(vm2_server_name, vm2_image_name,
                            vm2_origin_flavor_name)
        openstack_utils.check_status('ACTIVE', vm2_server_name, 20, 5)
        duration = self._do_resize(vm2_server_name, vm2_new_flavor_name)
        print('The duration is {}'.format(duration))

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

    def _write_remote_file(self):
        self._get_ssh_client()
        cmd = "echo 'Hello World!' > resize.data"
        self.client.execute(cmd)

    def _check_file_content(self):
        self._get_ssh_client()
        cmd = 'cat resize.data'
        status, stdout, stderr = self.client.execute(cmd)
        print(stdout.strip())

    def _create_server(self, server_name, image_name, flavor_name):
        nova_client = openstack_utils.get_nova_client()

        image = openstack_utils.get_image_by_name(image_name)

        flavor = openstack_utils.get_flavor_by_name(flavor_name)

        network = openstack_utils.get_network_by_name('ext-net')

        nic = [{'net-id': network.id}]

        return nova_client.servers.create(server_name, image, flavor, nics=nic)
