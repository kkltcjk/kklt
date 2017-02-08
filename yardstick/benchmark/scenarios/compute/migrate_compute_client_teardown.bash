mv /tmp/fstab /etc/fstab
umount host4:/

mv /tmp/libvirtd.conf /etc/libvirt/libvirtd.conf
mv /tmp/libvirt-bin.conf /etc/init/libvirt-bin.conf
mv /tmp/libvirt-bin /etc/default/libvirt-bin

stop libvirt-bin && start libvirt-bin


mv /tmp/nova.conf /etc/nova/nova.conf
service nova-compute restart
