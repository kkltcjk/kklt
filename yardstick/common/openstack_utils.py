##############################################################################
# Copyright (c) 2016 Huawei Technologies Co.,Ltd and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

from __future__ import absolute_import

import os
import time
import logging

from keystoneauth1 import loading
from keystoneauth1 import session
from novaclient import client as novaclient

log = logging.getLogger(__name__)

DEFAULT_HEAT_API_VERSION = '1'
DEFAULT_NOVA_API_VERSION = '2'


# *********************************************
#   CREDENTIALS
# *********************************************
def get_credentials():
    """Returns a creds dictionary filled with parsed from env"""
    creds = {}

    keystone_api_version = os.getenv('OS_IDENTITY_API_VERSION')

    if keystone_api_version is None or keystone_api_version == '2':
        keystone_v3 = False
        tenant_env = 'OS_TENANT_NAME'
        tenant = 'tenant_name'
    else:
        keystone_v3 = True
        tenant_env = 'OS_PROJECT_NAME'
        tenant = 'project_name'

    # The most common way to pass these info to the script is to do it
    # through environment variables.
    creds.update({
        "username": os.environ.get("OS_USERNAME"),
        "password": os.environ.get("OS_PASSWORD"),
        "auth_url": os.environ.get("OS_AUTH_URL"),
        tenant: os.environ.get(tenant_env)
    })

    if keystone_v3:
        if os.getenv('OS_USER_DOMAIN_NAME') is not None:
            creds.update({
                "user_domain_name": os.getenv('OS_USER_DOMAIN_NAME')
            })
        if os.getenv('OS_PROJECT_DOMAIN_NAME') is not None:
            creds.update({
                "project_domain_name": os.getenv('OS_PROJECT_DOMAIN_NAME')
            })

    cacert = os.environ.get("OS_CACERT")

    if cacert is not None:
        # each openstack client uses differnt kwargs for this
        creds.update({"cacert": cacert,
                      "ca_cert": cacert,
                      "https_ca_cert": cacert,
                      "https_cacert": cacert,
                      "ca_file": cacert})
        creds.update({"insecure": "True", "https_insecure": "True"})
        if not os.path.isfile(cacert):
            log.info("WARNING: The 'OS_CACERT' environment variable is set\
                      to %s but the file does not exist." % cacert)

    return creds


def get_session_auth():
    loader = loading.get_plugin_loader('password')
    creds = get_credentials()
    auth = loader.load_from_options(**creds)
    return auth


def get_session():
    auth = get_session_auth()
    return session.Session(auth=auth)


def get_endpoint(service_type, endpoint_type='publicURL'):
    auth = get_session_auth()
    return get_session().get_endpoint(auth=auth,
                                      service_type=service_type,
                                      endpoint_type=endpoint_type)


# *********************************************
#   CLIENTS
# *********************************************
def get_heat_api_version():
    api_version = os.getenv('HEAT_API_VERSION')
    if api_version is not None:
        log.info("HEAT_API_VERSION is set in env as '%s'", api_version)
        return api_version
    return DEFAULT_HEAT_API_VERSION


def get_nova_client_version():
    api_version = os.getenv('OS_COMPUTE_API_VERSION')
    if api_version is not None:
        log.info("OS_COMPUTE_API_VERSION is set in env as '%s'", api_version)
        return api_version
    return DEFAULT_NOVA_API_VERSION


def get_nova_client():
    sess = get_session()
    return novaclient.Client(get_nova_client_version(), session=sess)


# *********************************************
#   NOVA
# *********************************************
def get_instance_status(nova_client, instance):
    try:
        instance = nova_client.servers.get(instance.id)
        return instance.status
    except Exception, e:
        log.error("Error [get_instance_status(nova_client)]: %s" % e)
        return None


def get_instance_by_name(nova_client, instance_name):
    try:
        instance = nova_client.servers.find(name=instance_name)
        return instance
    except Exception, e:
        log.error("Error [get_instance_by_name(nova_client, '%s')]: %s"
                  % (instance_name, e))
        return None


def get_aggregates(nova_client):
    try:
        aggregates = nova_client.aggregates.list()
        return aggregates
    except Exception, e:
        log.error("Error [get_aggregates(nova_client)]: %s" % e)
        return None


def get_availability_zones(nova_client):
    try:
        availability_zones = nova_client.availability_zones.list()
        return availability_zones
    except Exception, e:
        log.error("Error [get_availability_zones(nova_client)]: %s" % e)
        return None


def get_availability_zone_names(nova_client):
    try:
        az_names = [az.zoneName for az in get_availability_zones(nova_client)]
        return az_names
    except Exception, e:
        log.error("Error [get_availability_zone_names(nova_client)]:"
                  " %s" % e)
        return None


def create_aggregate(nova_client, aggregate_name, av_zone):
    try:
        nova_client.aggregates.create(aggregate_name, av_zone)
        return True
    except Exception, e:
        log.error("Error [create_aggregate(nova_client, %s, %s)]: %s"
                  % (aggregate_name, av_zone, e))
        return None


def get_aggregate_id(nova_client, aggregate_name):
    try:
        aggregates = get_aggregates(nova_client)
        _id = [ag.id for ag in aggregates if ag.name == aggregate_name][0]
        return _id
    except Exception, e:
        log.error("Error [get_aggregate_id(nova_client, %s)]:"
                  " %s" % (aggregate_name, e))
        return None


def add_host_to_aggregate(nova_client, aggregate_name, compute_host):
    try:
        aggregate_id = get_aggregate_id(nova_client, aggregate_name)
        nova_client.aggregates.add_host(aggregate_id, compute_host)
        return True
    except Exception, e:
        log.error("Error [add_host_to_aggregate(nova_client, %s, %s)]: %s"
                  % (aggregate_name, compute_host, e))
        return None


def create_aggregate_with_host(
        nova_client, aggregate_name, av_zone, compute_host):
    try:
        create_aggregate(nova_client, aggregate_name, av_zone)
        add_host_to_aggregate(nova_client, aggregate_name, compute_host)
        return True
    except Exception, e:
        log.error("Error [create_aggregate_with_host("
                  "nova_client, %s, %s, %s)]: %s"
                  % (aggregate_name, av_zone, compute_host, e))
        return None


def create_instance(flavor_name,
                    image_id,
                    network_id,
                    instance_name="instance-vm",
                    confdrive=True,
                    userdata=None,
                    av_zone='',
                    fixed_ip=None,
                    files=None):
    nova_client = get_nova_client()
    try:
        flavor = nova_client.flavors.find(name=flavor_name)
    except:
        flavors = nova_client.flavors.list()
        log.error("Error: Flavor '%s' not found. Available flavors are: "
                  "\n%s" % (flavor_name, flavors))
        return None
    if fixed_ip is not None:
        nics = {"net-id": network_id, "v4-fixed-ip": fixed_ip}
    else:
        nics = {"net-id": network_id}
    if userdata is None:
        instance = nova_client.servers.create(
            name=instance_name,
            flavor=flavor,
            image=image_id,
            nics=[nics],
            availability_zone=av_zone,
            files=files
        )
    else:
        instance = nova_client.servers.create(
            name=instance_name,
            flavor=flavor,
            image=image_id,
            nics=[nics],
            config_drive=confdrive,
            userdata=userdata,
            availability_zone=av_zone,
            files=files
        )
    return instance


def create_instance_and_wait_for_active(flavor_name,
                                        image_id,
                                        network_id,
                                        instance_name="instance-vm",
                                        config_drive=False,
                                        userdata="",
                                        av_zone='',
                                        fixed_ip=None,
                                        files=None):
    SLEEP = 3
    VM_BOOT_TIMEOUT = 180
    nova_client = get_nova_client()
    instance = create_instance(flavor_name,
                               image_id,
                               network_id,
                               instance_name,
                               config_drive,
                               userdata,
                               av_zone=av_zone,
                               fixed_ip=fixed_ip,
                               files=files)
    count = VM_BOOT_TIMEOUT / SLEEP
    for n in range(count, -1, -1):
        status = get_instance_status(nova_client, instance)
        if status.lower() == "active":
            return instance
        elif status.lower() == "error":
            log.error("The instance %s went to ERROR status."
                      % instance_name)
            return None
        time.sleep(SLEEP)
    log.error("Timeout booting the instance %s." % instance_name)
    return None


def delete_instance(nova_client, instance_id):
    try:
        nova_client.servers.force_delete(instance_id)
        return True
    except Exception, e:
        log.error("Error [delete_instance(nova_client, '%s')]: %s"
                  % (instance_id, e))
        return False


def remove_host_from_aggregate(nova_client, aggregate_name, compute_host):
    try:
        aggregate_id = get_aggregate_id(nova_client, aggregate_name)
        nova_client.aggregates.remove_host(aggregate_id, compute_host)
        return True
    except Exception, e:
        log.error("Error [remove_host_from_aggregate(nova_client, %s, %s)]:"
                  " %s" % (aggregate_name, compute_host, e))
        return False


def remove_hosts_from_aggregate(nova_client, aggregate_name):
    aggregate_id = get_aggregate_id(nova_client, aggregate_name)
    hosts = nova_client.aggregates.get(aggregate_id).hosts
    assert(
        all(remove_host_from_aggregate(nova_client, aggregate_name, host)
            for host in hosts))


def delete_aggregate(nova_client, aggregate_name):
    try:
        remove_hosts_from_aggregate(nova_client, aggregate_name)
        nova_client.aggregates.delete(aggregate_name)
        return True
    except Exception, e:
        log.error("Error [delete_aggregate(nova_client, %s)]: %s"
                  % (aggregate_name, e))
        return False
