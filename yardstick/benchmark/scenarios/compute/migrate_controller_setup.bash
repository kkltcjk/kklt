nova_config_path=/etc/nova/nova.conf
cp -p "${nova_config_path}" /tmp/nova.conf
sed -i '/live_migration_flag/d' "${nova_config_path}"
sed -i '/DEFAULT/a live_migration_flag=VIR_MIGRATE_UNDEFINE_SOURCE,VIR_MIGRATE_PEER2PEER,VIR_MIGRATE_LIVE,VIR_MIGRATE_TUNNELLED' "${nova_config_path}"
sed -i '/vncserver_listen/d' "${nova_config_path}"
sed -i '/DEFAULT/a vncserver_listen=0.0.0.0' "${nova_config_path}"
sed -i '/scheduler_default_filters/d' "${nova_config_path}"
sed -i '/DEFAULT/a scheduler_default_filters=NUMATopologyFilter,AggregateInstanceExtraSpecsFilter' "${nova_config_path}"

service nova-scheduler restart
service nova-api restart
service nova-conductor restart
