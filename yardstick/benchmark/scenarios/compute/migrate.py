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
import subprocess
import threading
import time
import os

import yaml
import pkg_resources
from xml.etree import ElementTree as ET

from yardstick import ssh
from yardstick.common import openstack_utils
from yardstick.benchmark.scenarios import base
from yardstick.common import constants as consts
from yardstick.common.task_template import TaskTemplate

LOG = logging.getLogger(__name__)


class Migrate(base.Scenario):
    """
    Execute a live migration for two hosts

    """

    __scenario_type__ = "Migrate"

    PING = 'migrate_ping.bash'

    PRE_PATH = "yardstick.benchmark.scenarios.compute"

    def __init__(self, scenario_cfg, context_cfg):
        self.scenario_cfg = scenario_cfg
        self.context_cfg = context_cfg

        host = self.context_cfg['host']
        self.user = host.get('user', 'ubuntu')
        self.port = host.get("ssh_port", ssh.DEFAULT_PORT)
        self.ip = host.get('ip')
        self.key_filename = host.get('key_filename', '/root/.ssh/id_rsa')
        self.password = host.get('password')

        self.nova_client = openstack_utils.get_nova_client()

        node_file = os.path.join(consts.YARDSTICK_ROOT_PATH,
                                 scenario_cfg.get('node_file'))
        with open(node_file) as f:
            nodes = yaml.safe_load(TaskTemplate.render(f.read()))
        self.nodes = {a['name']: a for a in nodes['nodes']}

        options = self.scenario_cfg.get('options', {})
        host_list = options.get('host', '').split(',')
        self.controller_nodes = self._get_host_node(host_list, 'Controller')
        self.compute_nodes = self._get_host_node(host_list, 'Compute')

        self.cpu_set = options.get('cpu_set', '1,2,3,4,5,6')

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

    def _do_ping_task(self):
        destination = self.context_cfg['target'].get('ip')

        self._get_instance_client()
        ping_script = pkg_resources.resource_filename(Migrate.PRE_PATH,
                                                      Migrate.PING)
        self.instance_client._put_file_shell(ping_script,
                                             '~/{}'.format(Migrate.PING))
        cmd = 'sudo bash {} {}'.format(Migrate.PING, destination)

        ping_thread = PingThread(self.instance_client.execute, cmd)
        ping_thread.start()
        return ping_thread

    def _get_current_host_name(self, server_id):

        key = 'OS-EXT-SRV-ATTR:host'
        cmd = "openstack server show %s | grep %s | awk '{print $4}'" % (
            server_id, key)

        LOG.debug('Executing cmd: %s', cmd)
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
        current_host = p.communicate()[0].strip()

        LOG.debug('Host: %s', current_host)

        return current_host

    def run(self, result):
        targets = self.scenario_cfg.get('targets')
        vm1 = targets[0]

        status1, interrupt_time = self._do_first_job(vm1)
        LOG.debug('First job is %s', status1)

        vm2 = targets[1]
        status2 = self._do_second_job(vm2)
        LOG.debug('Second job is %s', status2)

        status = 1 if status1 and status2 else 0
        LOG.debug('The final status is %s', status)

        test_result = {
            'status': status,
            'interrupt_time': interrupt_time
        }

        result.update(test_result)

    def _do_first_job(self, target):
        ping_thread = self._do_ping_task()

        server = openstack_utils.get_server_by_name(target)

        current_host = self._get_current_host_name(server.id)

        host = self._get_migrate_host(current_host)
        LOG.debug('To be migrated: %s', host)

        cmd = ['nova', 'live-migration', server.id, host]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        LOG.debug('Migrated: %s', p.communicate()[0])

        time.sleep(10)
        current_host = self._get_current_host_name(server.id)

        status1 = True if host == current_host else False

        ping_thread.join()

        interrupt_time = self._compute_interrupt_time(ping_thread.get_result())
        LOG.debug('The interrupt time is %s ms', interrupt_time)

        LOG.debug('First Job Done')

        return status1, interrupt_time

    def _do_second_job(self, vm2):
        server = openstack_utils.get_server_by_name(vm2)

        current_host = self._get_current_host_name(server.id)

        info1 = self._check_numa_node(server.id, current_host)
        LOG.debug('Info before migrate: %s', info1)

        host = self._get_migrate_host(current_host)
        LOG.debug('To be migrated: %s', host)

        cmd = ['nova', 'live-migration', server.id, host]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        LOG.debug('Migrated: %s', p.communicate()[0])

        time.sleep(10)
        current_host = self._get_current_host_name(server.id)

        info2 = self._check_numa_node(server.id, current_host)
        LOG.debug('Info before migrate: %s', info2)

        LOG.debug('Second Job Done')

        numa_status = self._check_vm2_status(info1, info2)

        status2 = True if host == current_host and numa_status else False

        return status2

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

    def _check_numa_node(self, server_id, host):
        compute_node = 'node{}'.format(host.strip()[-1])
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

    def _get_migrate_host(self, current_host):
        hosts = self.nova_client.hosts.list_all()
        compute_hosts = [a.host for a in hosts if a.service == 'compute']
        for host in compute_hosts:
            if host.strip() != current_host.strip():
                return host

    def _compute_interrupt_time(self, data):
        times = data[1][:-2].split('.')
        start = int(times[1])
        end = int(times[0])
        return (end - start) / 1000000


class PingThread(threading.Thread):

    def __init__(self, method, args):
        super(PingThread, self).__init__()
        self.method = method
        self.args = args
        self.result = None

    def run(self):
        self.result = self.method(self.args)

    def get_result(self):
        return self.result
