#!/bin/bash
##############################################################################
# Copyright (c) 2017 Huawei Technologies Co.,Ltd and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

reset_aggregate()
{
    # Delete the "yardstick-pinned-flavor" flavor

    openstack flavor delete yardstick-pinned-flavor-1
    openstack flavor delete yardstick-pinned-flavor-2

    # Unset the "aggregate_instance_extra_specs:pinned" property on all existing flavors

    for FLAVOR in `nova flavor-list | grep "True" | cut -f 2 -d ' '`; \
        do openstack flavor unset --property \
            aggregate_instance_extra_specs:pinned ${FLAVOR}; \
        done

    # remove hosts from corresponding Nova aggregates

    nova aggregate-remove-host pinned-cpu host4
    # openstack aggregate remove host pinned-cpu host4

    nova aggregate-remove-host regular host5
    # openstack aggregate remove host regular host5

    # Delete created Nova aggregates

    openstack aggregate delete pinned-cpu

    openstack aggregate delete regular
}

reset_aggregate
