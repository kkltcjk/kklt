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

sed -i '/allow_resize_to_same_host/d' /etc/nova/nova.conf
sed -i '/scheduler_default_filters/d' /etc/nova/nova.conf

if which systemctl 2>/dev/null; then
  if [ $(systemctl is-active nova-scheduler.service) == "active" ]; then
      echo "restarting nova-scheduler.service"
      systemctl restart nova-scheduler.service
      systemctl restart nova-api.service
      systemctl restart nova-conductor.service
  elif [ $(systemctl is-active openstack-nova-scheduler.service) == "active" ]; then
      echo "restarting openstack-nova-scheduler.service"
      systemctl restart openstack-nova-scheduler.service
      systemctl restart openstack-nova-api.service
      systemctl restart openstack-nova-conductor.service
  fi
else
  if [[ $(service nova-scheduler status | grep running) ]]; then
    echo "restarting nova-scheduler.service"
    service nova-scheduler restart
    service nova-api restart
    service nova-conductor restart
  elif [[ $(service openstack-nova-scheduler status | grep running) ]]; then
    echo "restarting openstack-nova-scheduler.service"
    service openstack-nova-scheduler restart
    service openstack-nova-api restart
    service openstack-nova-conductor restart
  fi
fi
