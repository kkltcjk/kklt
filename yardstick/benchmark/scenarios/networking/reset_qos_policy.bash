#!/bin/bash
##############################################################################
# Copyright (c) 2017 Huawei Technologies Co.,Ltd and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

reset_qos_policy()
{
    # Delete the created QoS policy
    openstack network qos policy delete 100Mbps

    openstack network qos policy delete 1000Mbps
}

reset_qos_policy
