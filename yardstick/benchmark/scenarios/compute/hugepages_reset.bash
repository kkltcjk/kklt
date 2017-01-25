#!/bin/bash
##############################################################################
# Copyright (c) 2017 Huawei Technologies Co.,Ltd and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

openstack flavor delete yardstick-hugepages-flavor1
openstack flavor delete yardstick-hugepages-flavor2

for FLAVOR in `nova flavor-list | grep "True" | cut -f 2 -d ' '`; \
    do openstack flavor unset --property \
        aggregate_instance_extra_specs:pinned ${FLAVOR}; \
    done

nova aggregate-remove-host compute_node_1 overcloud-novacompute-0.opnfvlf.org
nova aggregate-remove-host compute_node_2 overcloud-novacompute-1.opnfvlf.org


openstack aggregate delete compute_node_1
openstack aggregate delete compute_node_2

