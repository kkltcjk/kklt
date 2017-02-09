#!/bin/bash
##############################################################################
# Copyright (c) 2017 Huawei Technologies Co.,Ltd and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

prepare_aggregate()
{
    # Create the "pinned-cpu" aggregate for hosts that will received pinning
    # requests.

    openstack aggregate create pinned-cpu

    # Create the "regular" aggregate for all other hosts.

    openstack aggregate create regular

    # Set metadata on the "pinned-cpu" aggregate, this will be used to match the
    # flavor we create shortly - here we are using the arbitrary key pinned and
    # setting it to true.

    nova aggregate-set-metadata pinned-cpu pinned=true
    # openstack aggregate set --property pinned=true pinned-cpu

    # Set metadata on the "regular" aggregate, this will be used to match all
    # existing "regular" flavors - here we are using the same key as before and
    # setting it to false.

    nova aggregate-set-metadata regular pinned=false
    # openstack aggregate set --property pinned=false regular

    # Add the existing compute nodes to the corresponding Nova aggregates.
    # Hosts that are not intended to be targets for pinned instances should be
    # added to the "regular" host aggregate

    compute_nodes=($(openstack availability zone list --long | grep nova-compute | sort | awk '{print $7}'))

    nova aggregate-add-host pinned-cpu ${compute_nodes[0]}
    # openstack aggregate add host pinned-cpu ${compute_nodes[0]}

    nova aggregate-add-host regular ${compute_nodes[1]}
    # openstack aggregate add host regular ${compute_nodes[1]}

    # Before creating the new flavor for cpu-pinning instances update all existing
    # flavors so that their extra specifications match them to the compute hosts in
    # the "regular" aggregate:

    for FLAVOR in `nova flavor-list | grep "True" | cut -f 2 -d ' '`; \
        do openstack flavor set --property \
            aggregate_instance_extra_specs:pinned=false ${FLAVOR}; \
        done

    # Create a new flavor "resize-flavor" for CPU pinning.
    # Set the hw:cpy_policy flavor extraspecification to dedicated. This denotes
    # that allinstances created using this flavor will require dedicated compute
    # resources and be pinned accordingly.
    # Set the aggregate_instance_extra_specs:pinned flavor extra specification to
    # true. This denotes that all instances created using this flavor will be sent
    # to hosts in host aggregates with pinned=true in their aggregate metadata:

    openstack flavor create --ram 512 --disk 3 --vcpus 2 resize-flavor-1
    openstack flavor create --ram 1024 --disk 3 --vcpus 2 resize-flavor-2

    # nova flavor-key resize-flavor set hw:cpu_policy=dedicated
    openstack flavor set --property hw:cpu_policy=dedicated resize-flavor-1
    openstack flavor set --property hw:cpu_policy=dedicated resize-flavor-2

    # nova flavor-key resize-flavor set aggregate_instance_extra_specs:pinned=true
    openstack flavor set --property aggregate_instance_extra_specs:pinned=true resize-flavor-1
    openstack flavor set --property aggregate_instance_extra_specs:pinned=true resize-flavor-2
}

prepare_aggregate
