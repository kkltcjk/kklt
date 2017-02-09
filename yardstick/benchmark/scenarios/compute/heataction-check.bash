openstack server show $1 | grep image | awk '{print $4}'
