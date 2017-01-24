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

CPU_SET=$1
HOST_MEMORY=$2

sed -i '/DEFAULT/a reserved_host_memory_mb='''${HOST_MEMORY}'''' /etc/nova/nova.conf
sed -i '/DEFAULT/a vcpu_pin_set='''${CPU_SET}'''' /etc/nova/nova.conf

if [ $(systemctl is-active nova-compute.service) == "active" ]; then
    echo "restarting nova-compute.service"
    systemctl restart nova-compute.service
elif [ $(systemctl is-active openstack-nova-compute.service) == "active" ]; then
    echo "restarting openstack-nova-compute.service"
    systemctl restart openstack-nova-compute.service
fi
