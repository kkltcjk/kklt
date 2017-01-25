#!/bin/bash
##############################################################################
# Copyright (c) 2017 Huawei Technologies Co.,Ltd and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

set -e

sudo sed -i '/vcpu_pin_set/d' /etc/nova/nova.conf
sudo sed -i '/reserved_host_memory_mb/d' /etc/nova/nova.conf

if [[ $(service nova-compute status | grep running) ]]; then
    echo "restarting nova-compute.service"
    service nova-compute restart
elif [[ $(service openstack-nova-compute status | grep running) ]]; then
    echo "restarting openstack-nova-compute.service"
    service openstack-nova-compute restart
fi
