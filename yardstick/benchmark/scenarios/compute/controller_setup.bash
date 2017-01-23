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

sed -i '/[DEFAULT]/a scheduler_default_filters=NUMATopologyFilter,AggregateInstanceExtraSpecsFilter' /etc/nova/nova.conf

systemctl restart nova-scheduler.service