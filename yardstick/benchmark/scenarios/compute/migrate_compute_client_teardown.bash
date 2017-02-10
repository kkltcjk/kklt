mv /tmp/group /etc/group
mv /tmp/passwd /etc/passwd

host=$1
umount "${host}:/var/lib/nova/instances"

service iptables save
setsebool -P virt_use_nfs 1

mv /tmp/libvirtd.conf /etc/libvirt/libvirtd.conf
mv /tmp/libvirtd /etc/sysconfig/libvirtd

mv /tmp/nova.conf /etc/nova/nova.conf

systemctl restart libvirtd.service
openstack-service restart
