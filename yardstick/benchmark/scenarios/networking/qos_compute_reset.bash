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

sed -i '/extensions/d' /etc/neutron/plugins/ml2/ml2_conf.ini

if which systemctl 2>/dev/null; then
  if [ $(systemctl is-active neutron-server.service) == "active" ]; then
      echo "restarting neutron-server.service"
      systemctl restart neutron-server.service
  elif [ $(systemctl is-active openstack-neutron-server.service) == "active" ]; then
      echo "restarting openstack-neutron-server.service"
      systemctl restart openstack-neutron-server.service
  fi
else
  if [[ $(service neutron-server status | grep running) ]]; then
    echo "restarting neutron-server.service"
    service neutron-server restart
  elif [[ $(service openstack-neutron-server status | grep running) ]]; then
    echo "restarting openstack-neutron-server.service"
    service openstack-neutron-server.service restart
  fi
fi
