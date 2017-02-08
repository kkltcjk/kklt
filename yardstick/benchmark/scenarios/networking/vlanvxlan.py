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

import logging

from yardstick.benchmark.scenarios import base
import yardstick.common.openstack_utils as op_utils

LOG = logging.getLogger(__name__)


class VlanVxlan(base.Scenario):
    """Test the ability for supporting vlan and vxlan network
    """
    __scenario_type__ = "VlanVxlan"

    def __init__(self, scenario_cfg, context_cfg):
        self.scenario_cfg = scenario_cfg
        self.context_cfg = context_cfg
        self.nova_client = op_utils.get_nova_client()
        self.testcase_status = 1
        self.setup_done = False

    def setup(self):
        '''scenario setup'''
        self.setup_done = True

    def run(self, result):
        """execute the benchmark"""
        if not self.setup_done:
            self.setup()

        for server in self.nova_client.servers.list():
            print(server.name, server.id, server.status, server.networks)
            if server.status != "ACTIVE":
                self.testcase_status = 0

        result.update({"Test": self.testcase_status})
