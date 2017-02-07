mv /tmp/nova.conf /etc/nova/nova.conf

service nova-scheduler restart
service nova-api restart
service nova-conductor restart
