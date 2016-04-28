# Copyright 2016 OSNEXUS Corporation
# See LICENSE file for details.

from flocker.node import BackendDescription, DeployerType
from osnexus_flocker_driver.osnexusdriver import *

def api_factory(cluster_id, **kwargs):
    return GetOsnexusStorageApi(kwargs[u"ipaddress"],kwargs[u"username"], kwargs[u"password"], kwargs[u"gold_tier"], kwargs[u"silver_tier"], kwargs[u"bronze_tier"], kwargs[u"default_pool"] )

FLOCKER_BACKEND = BackendDescription(
    name=u"osnexus_flocker_driver",
    needs_reactor=False, needs_cluster_id=True,
    api_factory=api_factory, deployer_type=DeployerType.block)
