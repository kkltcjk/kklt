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

    def __init__(self, scenario_cfg, context_cfg):
        self.scenario_cfg = scenario_cfg
        self.context_cfg = context_cfg

        host = self.context_cfg['host']
        self.user = host.get('user', 'ubuntu')
        self.port = host.get("ssh_port", ssh.DEFAULT_PORT)
        self.ip = host.get('ip')
        self.key_filename = host.get('key_filename', '/root/.ssh/id_rsa')
        self.password = host.get('password')

        options = scenario_cfg['options']
        host_list = options.get('host').split(',')

        self.cpu_set = options.get("cpu_set", '1,2,3,4,5,6')
        self.host_memory = options.get("host_memory", 512)

        self.nova_client = openstack_utils.get_nova_client()
        self.neutron_client = openstack_utils.get_neutron_client()
        self.glance_client = openstack_utils.get_glance_client()

        node_file = os.path.join(consts.YARDSTICK_ROOT_PATH,
                                 scenario_cfg.get('node_file'))
        with open(node_file) as f:
            nodes = yaml.safe_load(TaskTemplate.render(f.read()))
        self.nodes = {a['name']: a for a in nodes['nodes']}

        self.controller_nodes = self._get_host_node(host_list, 'Controller')
        self.compute_nodes = self._get_host_node(host_list, 'Compute')

    def _get_host_node(self, hosts, type):
        nodes = [a for a in hosts if self.nodes.get(a, {}).get('role') == type]

        if not nodes:
            LOG.error("Can't find %s node in the context!!!", type)

        return nodes

    def _get_host_client(self, node_name):
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

    def _write_remote_file(self, word):
        self._get_instance_client()
        cmd = "echo {} > resize.data".format(word)
        self.instance_client.execute(cmd)

    def _check_file_content(self, word):
        self._get_instance_client()
        cmd = 'cat resize.data'
        status, stdout, stderr = self.instance_client.execute(cmd)
        return word == stdout.strip()

    def run(self, result):

        status1, duration1 = self._do_first_job()

        status2, duration2 = self._do_second_job()

        status = 1 if status1 and status2 else 0
        LOG.debug('The final status is %s', status)

        test_result = {
            'status': status,
            'duration1': duration1,
            'duration2': duration2
        }

        LOG.debug('The result data is %s', test_result)

        result.update(test_result)

    def _do_first_job(self):
        word = 'Hello world!'
        self._write_remote_file(word)

        vm1 = self.scenario_cfg['host']
        new_flavor = self.scenario_cfg['vm1_new_flavor']

        duration1 = self._do_resize(vm1, new_flavor)
        LOG.debug('Resize Success! The duration is %s', duration1)

        status1 = self._check_file_content(word)
        LOG.debug('First Job status is: %s', status1)

        return status1, duration1

    def _do_second_job(self):
        vm2 = self.scenario_cfg.get('target')
        server = openstack_utils.get_server_by_name(vm2)

        new_flavor = self.scenario_cfg['vm2_new_flavor']

        data1 = self._check_numa_node(server.id)
        LOG.debug('Data before resize: %s', data1)

        duration2 = self._do_resize(vm2, new_flavor)
        LOG.debug('Resize Success! The duration is %s', duration2)

        data2 = self._check_numa_node(server.id)
        LOG.debug('Data after resize: %s', data2)

        status2 = self._check_vm2_status(data1, data2)
        LOG.debug('Second Job status is: %s', status2)

        return status2, duration2

    def _check_vm2_status(self, info1, info2):
        nodepin_ok = True
        for i in info1['pinning']:
            ok = 0
            for j in info2['pinning']:
                if i['nodeset'] == j['nodeset']:
                    ok = 1
                    break
            if ok == 0:
                nodepin_ok = False
                break

        vcpupin_ok = True
        for i in info2['vcpupin']:
            for j in i['cpuset'].split(','):
                if j not in self.cpu_set.split(','):
                    vcpupin_ok = False
                    break

        return nodepin_ok and vcpupin_ok

    def _check_numa_node(self, server_id):
        for compute_node in self.compute_nodes:
            self._get_host_client(compute_node)

        cmd = "virsh dumpxml %s" % server_id
        LOG.debug("Executing command: %s", cmd)
        status, stdout, stderr = self.host_client.execute(cmd)
        if status:
            raise RuntimeError(stderr)
        root = ET.fromstring(stdout)
        vcpupin = [a.attrib for a in root.iter('vcpupin')]
        pinning = [a.attrib for a in root.iter('memnode')]
        return {"pinning": pinning, 'vcpupin': vcpupin}

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
