#!/usr/bin/env python

##############################################################################
# Copyright (c) 2017 Huawei Technologies Co.,Ltd and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

# Unittest for yardstick.benchmark.scenarios.networking.attachnic.AttachNic

from __future__ import absolute_import
import mock
import unittest

from yardstick.benchmark.scenarios.networking import attachnic


class AttachNicTestCase(unittest.TestCase):

    def setUp(self):
        self.ctx = {
            'host': {
                'ip': '172.16.0.137',
                'user': 'cirros',
                'key_filename': "mykey.key"
            },
            "target": {
                "ipaddr": "10.229.17.105",
            }
        }

    @mock.patch('yardstick.benchmark.scenarios.networking.attachnic.ssh')
    def test_attachnic_successful(self, mock_ssh):

        args = {
            'options': {'packetsize': 200},
            'target': 'ares.demo'
            }
        result = {}

        att = attachnic.AttachNic(args, self.ctx)

        mock_ssh.SSH().execute.return_value = (0, '100', '')
        att.run(result)
        self.assertEqual(result, {'NIC': '100', 'rtt': {'ares': 100.0}})

    @mock.patch('yardstick.benchmark.scenarios.networking.attachnic.ssh')
    def test_attachnic_unsuccessful_script_error(self, mock_ssh):

        args = {
            'options': {'packetsize': 200},
            'sla': {'max_rtt': 50},
            'target': 'ares.demo'
        }
        result = {}

        att = attachnic.AttachNic(args, self.ctx)

        mock_ssh.SSH().execute.return_value = (1, '', 'FOOBAR')
        self.assertRaises(RuntimeError, att.run, result)


def main():
    unittest.main()

if __name__ == '__main__':
    main()
