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

sed -i 's/^service_plugins =.*/&,neutron.services.qos.qos_plugin.QoSPlugin/' /etc/neutron/neutron.conf
sed -i 's/^extension_drivers =.*/&,qos/' /etc/neutron/plugins/ml2/ml2_conf.ini
sed -i '/^\[agent/a extensions = qos' /etc/neutron/plugins/ml2/openvswitch_agent.ini

if which systemctl 2>/dev/null; then
  if [ $(systemctl is-active neutron-server.service) == "active" ]; then
      echo "restarting neutron-server.service"
      systemctl restart neutron-server.service
  elif [ $(systemctl is-active openstack-neutron-server.service) == "active" ]; then
      echo "restarting openstack-neutron-server.service"
      systemctl restart openstack-neutron-server.service
  fi
  if [ $(systemctl is-active neutron-openvswitch-agent.service) == "active" ]; then
      echo "restarting neutron-openvswitch-agent.service"
      systemctl restart neutron-openvswitch-agent.service
  elif [ $(systemctl is-active openstack-neutron-openvswitch-agent.service) == "active" ]; then
      echo "restarting openstack-neutron-openvswitch-agent.service"
      systemctl restart openstack-neutron-openvswitch-agent.service
  fi
else
  if [[ $(service neutron-server status | grep running) ]]; then
    echo "restarting neutron-server.service"
    service neutron-server restart
  elif [[ $(service openstack-neutron-server status | grep running) ]]; then
    echo "restarting openstack-neutron-server.service"
    service openstack-neutron-server.service restart
  fi
  if [[ $(service neutron-openvswitch-agent status | grep running) ]]; then
    echo "restarting neutron-openvswitch-agent.service"
    service neutron-openvswitch-agent restart
  elif [[ $(service openstack-neutron-openvswitch-agent status | grep running) ]]; then
    echo "restarting openstack-neutron-openvswitch-agent.service"
    service openstack-neutron-openvswitch-agent.service restart
  fi
fi
