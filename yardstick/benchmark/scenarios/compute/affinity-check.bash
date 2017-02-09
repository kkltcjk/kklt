vm=$(openstack server list | grep $1 | awk '{print $4}')
openstack server show $vm | grep OS-EXT-SRV-ATTR:host | awk '{print $4}'
