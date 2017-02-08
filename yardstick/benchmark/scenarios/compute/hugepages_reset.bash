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

compute_nodes=($(openstack availability zone list --long | grep nova-compute | awk '{print $7}' | sort))
openstack aggregate remove host compute_node_1 ${compute_nodes[0]}
openstack aggregate remove host compute_node_2 ${compute_nodes[1]}

openstack aggregate delete compute_node_1
openstack aggregate delete compute_node_2

