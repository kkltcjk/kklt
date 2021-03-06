#!/usr/bin/env python

##############################################################################
# Copyright (c) 2015 Ericsson AB and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

# Unittest for yardstick.benchmark.scenarios.networking.pktgen.Pktgen

from __future__ import absolute_import

import unittest

import mock
from oslo_serialization import jsonutils

from yardstick.benchmark.scenarios.networking import pktgen


@mock.patch('yardstick.benchmark.scenarios.networking.pktgen.ssh')
class PktgenTestCase(unittest.TestCase):

    def setUp(self):
        self.ctx = {
            'host': {
                'ip': '172.16.0.137',
                'user': 'root',
                'key_filename': 'mykey.key'
            },
            'target': {
                'ip': '172.16.0.138',
                'user': 'root',
                'key_filename': 'mykey.key',
                'ipaddr': '172.16.0.138'
            }
        }

    def test_pktgen_successful_setup(self, mock_ssh):

        args = {
            'options': {'packetsize': 60},
        }
        p = pktgen.Pktgen(args, self.ctx)
        p.setup()

        mock_ssh.SSH().execute.return_value = (0, '', '')
        self.assertIsNotNone(p.server)
        self.assertIsNotNone(p.client)
        self.assertEqual(p.setup_done, True)

    def test_pktgen_successful_iptables_setup(self, mock_ssh):

        args = {
            'options': {'packetsize': 60, 'number_of_ports': 10},
        }
        p = pktgen.Pktgen(args, self.ctx)
        p.server = mock_ssh.SSH()
        p.number_of_ports = args['options']['number_of_ports']

        mock_ssh.SSH().execute.return_value = (0, '', '')

        p._iptables_setup()

        mock_ssh.SSH().execute.assert_called_with(
            "sudo iptables -F; "
            "sudo iptables -A INPUT -p udp --dport 1000:%s -j DROP"
            % 1010)

    def test_pktgen_unsuccessful_iptables_setup(self, mock_ssh):

        args = {
            'options': {'packetsize': 60, 'number_of_ports': 10},
        }

        p = pktgen.Pktgen(args, self.ctx)
        p.server = mock_ssh.SSH()
        p.number_of_ports = args['options']['number_of_ports']

        mock_ssh.SSH().execute.return_value = (1, '', 'FOOBAR')
        self.assertRaises(RuntimeError, p._iptables_setup)

    def test_pktgen_successful_iptables_get_result(self, mock_ssh):

        args = {
            'options': {'packetsize': 60, 'number_of_ports': 10},
        }

        p = pktgen.Pktgen(args, self.ctx)
        p.server = mock_ssh.SSH()
        p.number_of_ports = args['options']['number_of_ports']

        mock_ssh.SSH().execute.return_value = (0, '150000', '')
        p._iptables_get_result()

        mock_ssh.SSH().execute.assert_called_with(
            "sudo iptables -L INPUT -vnx |"
            "awk '/dpts:1000:%s/ {{printf \"%%s\", $1}}'"
            % 1010)

    def test_pktgen_unsuccessful_iptables_get_result(self, mock_ssh):

        args = {
            'options': {'packetsize': 60, 'number_of_ports': 10},
        }

        p = pktgen.Pktgen(args, self.ctx)

        p.server = mock_ssh.SSH()
        p.number_of_ports = args['options']['number_of_ports']

        mock_ssh.SSH().execute.return_value = (1, '', 'FOOBAR')
        self.assertRaises(RuntimeError, p._iptables_get_result)

    def test_pktgen_successful_no_sla(self, mock_ssh):

        args = {
            'options': {'packetsize': 60, 'number_of_ports': 10},
        }
        result = {}

        p = pktgen.Pktgen(args, self.ctx)

        p.server = mock_ssh.SSH()
        p.client = mock_ssh.SSH()

        mock_iptables_result = mock.Mock()
        mock_iptables_result.return_value = 149300
        p._iptables_get_result = mock_iptables_result

        sample_output = '{"packets_per_second": 9753, "errors": 0, \
            "packets_sent": 149776, "flows": 110}'
        mock_ssh.SSH().execute.return_value = (0, sample_output, '')

        p.run(result)
        expected_result = jsonutils.loads(sample_output)
        expected_result["packets_received"] = 149300
        self.assertEqual(result, expected_result)

    def test_pktgen_successful_sla(self, mock_ssh):

        args = {
            'options': {'packetsize': 60, 'number_of_ports': 10},
            'sla': {'max_ppm': 10000}
        }
        result = {}

        p = pktgen.Pktgen(args, self.ctx)

        p.server = mock_ssh.SSH()
        p.client = mock_ssh.SSH()

        mock_iptables_result = mock.Mock()
        mock_iptables_result.return_value = 149300
        p._iptables_get_result = mock_iptables_result

        sample_output = '{"packets_per_second": 9753, "errors": 0, \
            "packets_sent": 149776, "flows": 110}'
        mock_ssh.SSH().execute.return_value = (0, sample_output, '')

        p.run(result)
        expected_result = jsonutils.loads(sample_output)
        expected_result["packets_received"] = 149300
        self.assertEqual(result, expected_result)

    def test_pktgen_unsuccessful_sla(self, mock_ssh):

        args = {
            'options': {'packetsize': 60, 'number_of_ports': 10},
            'sla': {'max_ppm': 1000}
        }
        result = {}

        p = pktgen.Pktgen(args, self.ctx)

        p.server = mock_ssh.SSH()
        p.client = mock_ssh.SSH()

        mock_iptables_result = mock.Mock()
        mock_iptables_result.return_value = 149300
        p._iptables_get_result = mock_iptables_result

        sample_output = '{"packets_per_second": 9753, "errors": 0, \
            "packets_sent": 149776, "flows": 110}'
        mock_ssh.SSH().execute.return_value = (0, sample_output, '')
        self.assertRaises(AssertionError, p.run, result)

    def test_pktgen_unsuccessful_script_error(self, mock_ssh):

        args = {
            'options': {'packetsize': 60, 'number_of_ports': 10},
            'sla': {'max_ppm': 1000}
        }
        result = {}

        p = pktgen.Pktgen(args, self.ctx)

        p.server = mock_ssh.SSH()
        p.client = mock_ssh.SSH()

        mock_ssh.SSH().execute.return_value = (1, '', 'FOOBAR')
        self.assertRaises(RuntimeError, p.run, result)


def main():
    unittest.main()

if __name__ == '__main__':
    main()
