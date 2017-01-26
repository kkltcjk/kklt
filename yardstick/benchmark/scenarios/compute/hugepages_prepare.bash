#!/bin/bash
##############################################################################
# Copyright (c) 2017 Huawei Technologies Co.,Ltd and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


openstack aggregate create compute_node_1

openstack aggregate create compute_node_2

nova aggregate-set-metadata compute_node_1 hugepagesz=2m

nova aggregate-set-metadata compute_node_2 hugepagesz=1g

nova aggregate-add-host compute_node_1 overcloud-novacompute-0.opnfvlf.org

nova aggregate-add-host compute_node_2 overcloud-novacompute-1.opnfvlf.org

for FLAVOR in `nova flavor-list | grep "True" | cut -f 2 -d ' '`; \
    do openstack flavor set --property \
        aggregate_instance_extra_specs:pinned=false ${FLAVOR}; \
    done


openstack flavor create --id 601 --ram 512 --disk 3 --vcpus 2 yardstick-hugepages-flavor1
openstack flavor create --id 601 --ram 512 --disk 3 --vcpus 2 yardstick-hugepages-flavor2

openstack flavor set yardstick-hugepages-flavor1 --property hw:mem_page_size=2048
openstack flavor set yardstick-hugepages-flavor2 --property hw:mem_page_size=1024Mb

openstack flavor set --property hw:cpu_policy=dedicated yardstick-hugepages-flavor1
openstack flavor set --property hw:cpu_policy=dedicated yardstick-hugepages-flavor2

openstack flavor set --property aggregate_instance_extra_specs:hugepagesz=2m yardstick-hugepages-flavor1
openstack flavor set --property aggregate_instance_extra_specs:hugepagesz=1g yardstick-hugepages-flavor2
