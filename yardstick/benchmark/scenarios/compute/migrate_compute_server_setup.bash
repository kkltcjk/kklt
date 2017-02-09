apt_config_path='/etc/apt/sources.list'
cp -p "${apt_config_path}" /tmp/sources.list
sed -i '$a deb [arch=amd64] http://archive.ubuntu.com/ubuntu/ trusty main restricted' "${apt_config_path}"
sed -i '$a deb [arch=amd64] http://archive.ubuntu.com/ubuntu/ trusty-updates main restricted' "${apt_config_path}"
apt-get update && apt-get install nfs-kernel-server

nfs_config_path='/etc/exports'
cp -p "${nfs_config_path}" /tmp/exports
sed -i '$a /var/lib/nova/instances 172.16.1.4/255.255.255.0(rw,sync,fsid=0,no_root_squash,no_subtree_check)' "${nfs_config_path}"
/etc/init.d/nfs-kernel-server restart

libvirtd_config_path='/etc/libvirt/libvirtd.conf'
cp -p "${libvirtd_config_path}" /tmp/libvirtd.conf
sed -i '/listen_tls/d' "${libvirtd_config_path}"
sed -i '$a listen_tls = 0' "${libvirtd_config_path}"
sed -i '/listen_tcp/d' "${libvirtd_config_path}"
sed -i '$a listen_tcp = 1' "${libvirtd_config_path}"
sed -i '/auth_tcp/d' "${libvirtd_config_path}"
sed -i '$a auth_tcp="none"' "${libvirtd_config_path}"

libvirt_bin_config_path='/etc/init/libvirt-bin.conf'
cp -p "${libvirt_bin_config_path}" /tmp/libvirt-bin.conf
sed -i 's/env libvirtd_opts="-d"/env libvirtd_opts="-d -l"/g' "${libvirt_bin_config_path}"

libvirt_bin_path='/etc/default/libvirt-bin'
cp -p "${libvirt_bin_path}" /tmp/libvirt-bin
sed -i '/libvirtd_opts/d' "${libvirt_bin_path}"
sed -i '$a libvirtd_opts="-d -l"' "${libvirt_bin_path}"

stop libvirt-bin && start libvirt-bin


CPU_SET=$1
HOST_MEMORY=$2
nova_config_path='/etc/nova/nova.conf'
cp -p "${nova_config_path}" /tmp/nova.conf
sed -i '/live_migration_flag/d' "${nova_config_path}"
sed -i '/DEFAULT/a live_migration_flag=VIR_MIGRATE_UNDEFINE_SOURCE,VIR_MIGRATE_PEER2PEER,VIR_MIGRATE_LIVE,VIR_MIGRATE_TUNNELLED' "${nova_config_path}"
sed -i '/vncserver_listen/d' "${nova_config_path}"
sed -i '/DEFAULT/a vncserver_listen=0.0.0.0' "${nova_config_path}"

sed -i '/reserved_host_memory_mb/d' "${nova_config_path}"
sed -i '/DEFAULT/a reserved_host_memory_mb='''${HOST_MEMORY}'''' "${nova_config_path}"
sed -i '/vcpu_pin_set/d' "${nova_config_path}"
sed -i '/DEFAULT/a vcpu_pin_set='''${CPU_SET}'''' "${nova_config_path}"

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
