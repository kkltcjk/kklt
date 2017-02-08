#!/bin/bash
##############################################################################
# Copyright (c) 2017 Huawei Technologies Co.,Ltd and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

set -x

openstack aggregate create compute_node_1
openstack aggregate create compute_node_2

nova aggregate-set-metadata compute_node_1 hugepagesz=2M
nova aggregate-set-metadata compute_node_2 hugepagesz=1G

compute_nodes=($(openstack availability zone list --long | grep nova-compute | awk '{print $7}'))

nova aggregate-add-host compute_node_1 ${compute_nodes[0]}
nova aggregate-add-host compute_node_2 ${compute_nodes[1]}

openstack flavor create --ram 1024 --disk 3 --vcpus 2 yardstick-hugepages-flavor1
openstack flavor create --ram 1024 --disk 3 --vcpus 2 yardstick-hugepages-flavor2

openstack flavor set yardstick-hugepages-flavor1 --property hw:mem_page_size=2048
openstack flavor set yardstick-hugepages-flavor2 --property hw:mem_page_size=1048576

openstack flavor set --property hw:cpu_policy=dedicated yardstick-hugepages-flavor1
openstack flavor set --property hw:cpu_policy=dedicated yardstick-hugepages-flavor2

openstack flavor set --property aggregate_instance_extra_specs:hugepagesz=2M yardstick-hugepages-flavor1
openstack flavor set --property aggregate_instance_extra_specs:hugepagesz=1G yardstick-hugepages-flavor2
