#!/bin/bash
##############################################################################
# Copyright (c) 2017 Huawei Technologies Co.,Ltd and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

prepare_qos_policy()
{
    # First, create a QoS policy named '100Mbps' and its bandwidth limit rules:
    openstack network qos policy create 100Mbps
    # neutron qos-policy-create 100Mbps

    # openstack network qos rule create --max-kbps 100000 100Mbps
    neutron qos-bandwidth-limit-rule-create 100Mbps --max-kbps 50000 --max-burst-kbps 300

    # Second, create a QoS policy named '1000Mbps' and its bandwidth limit rules:
    openstack network qos policy create 1000Mbps
    # neutron qos-policy-create 1000Mbps

    # openstack network qos rule create --max-kbps 1000000 1000Mbps
    neutron qos-bandwidth-limit-rule-create 1000Mbps --max-kbps 1000000 --max-burst-kbps 300
}

prepare_qos_policy
