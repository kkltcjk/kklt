mv /tmp/nfs /etc/sysconfig/nfs
mv /tmp/group /etc/group
mv /tmp/passwd /etc/passwd
mv /tmp/exports /etc/exports

systemctl start nfs-server.service
systemctl enable nfs-server.service
systemctl restart iptables.service

exportfs -avr

mv /tmp/libvirtd.conf /etc/libvirt/libvirtd.conf
mv /tmp/libvirtd /etc/sysconfig/libvirtd

mv /tmp/nova.conf /etc/nova/nova.conf

systemctl restart libvirtd.service
openstack-service restart
