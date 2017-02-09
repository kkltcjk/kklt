mv /tmp/sources.list /etc/apt/sources.list

mv /tmp/exports /etc/exports
/etc/init.d/nfs-kernel-server restart

mv /tmp/libvirtd.conf /etc/libvirt/libvirtd.conf
mv /tmp/libvirt-bin.conf /etc/init/libvirt-bin.conf
mv /tmp/libvirt-bin /etc/default/libvirt-bin

stop libvirt-bin && start libvirt-bin


mv /tmp/nova.conf /etc/nova/nova.conf
if which systemctl 2>/dev/null; then
  if [ $(systemctl is-active nova-compute.service) == "active" ]; then
      echo "restarting nova-compute.service"
      systemctl restart nova-compute.service
  elif [ $(systemctl is-active openstack-nova-compute.service) == "active" ]; then
      echo "restarting openstack-nova-compute.service"
      systemctl restart openstack-nova-compute.service
  fi
else
  if [[ $(service nova-compute status | grep running) ]]; then
    echo "restarting nova-compute.service"
    service nova-compute restart
  elif [[ $(service openstack-nova-compute status | grep running) ]]; then
    echo "restarting openstack-nova-compute.service"
    service openstack-nova-compute restart
  fi
fi
