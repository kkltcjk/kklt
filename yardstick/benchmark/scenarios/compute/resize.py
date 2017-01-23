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
import pkg_resources
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

    TARGET_SCRIPT = 'resize.bash'

    def __init__(self, scenario_cfg, context_cfg):
        self.scenario_cfg = scenario_cfg
        self.context_cfg = context_cfg
        self.target_script = pkg_resources.resource_filename(
            'yardstick.benchmark.scenarios.compute', Resize.TARGET_SCRIPT)

        print('\n{}'.format(scenario_cfg))
        print('{}\n'.format(context_cfg))

    def _get_ssh_client(self):
        host = self.context_cfg['host']
        user = host.get('user', 'ubuntu')
        ssh_port = host.get("ssh_port", ssh.DEFAULT_PORT)
        ip = host.get('ip')
        key = host.get('key_filename', '/root/.ssh/id_rsa')
        password = host.get('password')

        if password is not None:
            LOG.info("Log in via pw, user:%s, host:%s, pw:%s",
                     user, ip, password)
            self.client = ssh.SSH(user, ip, password=password, port=ssh_port)
        else:
            LOG.info("Log in via key, user:%s, host:%s, key_filename:%s",
                     user, ip, key)
            self.client = ssh.SSH(user, ip, key_filename=key, port=ssh_port)

        self.client.wait(timeout=600)

    def run(self, result):
        self._get_ssh_client()
        self.client._put_file_shell(self.target_script, '~/resize.bash')
        cmd = '/bin/sh resize.bash'
        status, stdout, stderr = self.client.execute(cmd)

        server_name = self.scenario_cfg['host']
        new_flavor_name = self.scenario_cfg['new_flavor']

        nova_client = openstack_utils.get_nova_client()

        server_id = openstack_utils.get_server_by_name(server_name).id
        new_flavor = openstack_utils.get_flavor_by_name(new_flavor_name)

        t1 = datetime.now()
        nova_client.servers.resize(server_id, new_flavor)
        openstack_utils.check_status('VERIFY_RESIZE', server_name, 100, 1)
        nova_client.servers.confirm_resize(server_id)
        t2 = datetime.now()
        duration = (t2 - t1).seconds
        print('The duration is {}'.format(duration))

        self._get_ssh_client()
        cmd = 'cat resize.data'
        status, stdout, stderr = self.client.execute(cmd)
        print(stdout)

    def _create_server(self, server_name, image_name, flavor_name):
        nova_client = openstack_utils.get_nova_client()

        image = openstack_utils.get_image(image_name)

        flavor = openstack_utils.get_flavor(flavor_name)

        return nova_client.servers.create(server_name, image, flavor)
