yum install iptables openstack-utils openstack-nova-novncproxy -y
systemctl start rpcbind.service

group_path='/etc/group'
cp -p "${group_path}" /tmp/group
sed -i '/^nova/d' "${group_path}"
sed -i '$a nova:x:162:nova' "${group_path}"

passwd_path='/etc/passwd'
cp -p "${passwd_path}" /tmp/passwd
sed -i '/^nova/d' "${passwd_path}"
sed -i '$a nova:x:162:162:OpenStack Nova Daemons:/var/lib/nova:/sbin/nologin' "${passwd_path}"

mkdir -p /var/lib/nova/instances
chmod 775 /var/lib/nova/instances

host=$3
mount -t nfs "${host}:/var/lib/nova/instances" /var/lib/nova/instances

iptables -v -I INPUT 1 -p tcp --dport 16509 -j ACCEPT
iptables -v -I INPUT 1 -p tcp --dport 16514 -j ACCEPT
iptables -v -I INPUT -p tcp --dport 49152:49215 -j ACCEPT
iptables -v -N NFS; iptables -v -I INPUT -j NFS

service iptables save
setsebool -P virt_use_nfs 1

libvirtd_conf_path='/etc/libvirt/libvirtd.conf'
cp -p "${libvirtd_conf_path}" /tmp/libvirtd.conf
sed -i '/listen_tls/d' "${libvirtd_conf_path}"
sed -i '$a listen_tls = 0' "${libvirtd_conf_path}"
sed -i '/listen_tcp/d' "${libvirtd_conf_path}"
sed -i '$a listen_tcp = 1' "${libvirtd_conf_path}"
sed -i '/auth_tcp/d' "${libvirtd_conf_path}"
sed -i '$a auth_tcp="none"' "${libvirtd_conf_path}"

libvirtd_path='/etc/sysconfig/libvirtd'
cp -p "${libvirtd_path}" /tmp/libvirtd
sed -i '/LIBVIRTD_ARGS/d' "${libvirtd_path}"
sed -i '$a LIBVIRTD_ARGS="--listen"' "${libvirtd_path}"

CPU_SET=$1
HOST_MEMORY=$2
nova_path='/etc/nova/nova.conf'
cp -p "${nova_path}" /tmp/nova.conf
sed -i '/live_migration_uri/d' "${nova_path}"
sed -i '/DEFAULT/a live_migration_uri=qemu+tcp://nova@%s/system' "${nova_path}"
sed -i '/reserved_host_memory_mb/d' "${nova_path}"
sed -i '/DEFAULT/a reserved_host_memory_mb='''${HOST_MEMORY}'''' "${nova_path}"
sed -i '/vcpu_pin_set/d' "${nova_path}"
sed -i '/DEFAULT/a vcpu_pin_set='''${CPU_SET}'''' "${nova_path}"


systemctl restart libvirtd.service
openstack-config --set /etc/nova/nova.conf DEFAULT vncserver_listen 0.0.0.0
openstack-config --set /etc/nova/nova.conf DEFAULT live_migration_flag VIR_MIGRATE_UNDEFINE_SOURCE,VIR_MIGRATE_PEER2PEER,VIR_MIGRATE_LIVE
openstack-service restart

