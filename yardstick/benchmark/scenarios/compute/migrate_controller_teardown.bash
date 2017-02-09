mv /tmp/nova.conf /etc/nova/nova.conf

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
