# Copyright 2016 OSNEXUS Corporation

"""
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
 http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""



import socket
from zope.interface import implementer
from flocker.node.agents.blockdevice import (
    AlreadyAttachedVolume, IBlockDeviceAPI, IProfiledBlockDeviceAPI,
    BlockDeviceVolume, UnknownVolume, UnattachedVolume
)
from osnexusutil import osnexusAPI
import logging
from eliot import Message, Logger

#_logger = Logger()

@implementer(IProfiledBlockDeviceAPI)
@implementer(IBlockDeviceAPI)
class OsnexusBlockDeviceAPI(object):

    defaultVolumeBlkSize_ = 4096
    defaultCreatedBy_ = "osnexus_flocker_driver"
    defaultExportedBlkSize_ = 4096

    def __init__(self, ipaddress, username, password, gold_tier, silver_tier, bronze_tier, default_pool):
        """
        :returns: A ``BlockDeviceVolume``.
        """
        logging.basicConfig(filename='/var/log/flocker/qs_flocker.log', format='%(asctime)s : %(message)s', level=logging.ERROR)
        self._logger = logging.getLogger("QuantastorLogger")

        self._instance_id = self.compute_instance_id()

        self._osnexusApi = osnexusAPI(ipaddress, username, password, gold_tier, silver_tier, bronze_tier, default_pool, self._logger)

    def compute_instance_id(self):
        """
        Return current node's hostname
        """
        #socket.getfqdn - Return a fully qualified domain name for name. If name is omitted or empty, it is interpreted
        #as the local host. In case no fully qualified domain name is available, the hostname as returned by
        # gethostname() is returned.
        #socket.gethostbyname - Translate a host name to IPv4 address format.

        return unicode(socket.gethostbyname(socket.getfqdn()))


    def allocation_unit(self):
        """
        return int: 1 GB
        """
        return 1024*1024*1024

    def _cleanup(self):
        """
        Remove all volumes
        """
        volumes = self.list_volumes()
        for volume in volumes:
            self._logger.debug("Deleting volume '%s'", volume.blockdevice_id)
            self.destroy_volume(volume.blockdevice_id)

    def list_volumes(self):
        """
        List all the block devices available via the back end API.
        :returns: A ``list`` of ``BlockDeviceVolume``s.
        """
        return self._osnexusApi.listOsnexusVolumes()


    def create_volume(self, dataset_id, size):
        return self._osnexusApi.createOsnexusVolume(dataset_id, size)

    def create_volume_with_profile(self, dataset_id, size, profile_name):
        return self._osnexusApi.createOsnexusVolumeWithProfile(dataset_id, size, profile_name.lower())

    def destroy_volume(self, blockdevice_id):
        return self._osnexusApi.deleteOsnexusVolume(blockdevice_id)

    def attach_volume(self, blockdevice_id, attach_to):
        return self._osnexusApi.attachOsnexusVolume(blockdevice_id, attach_to)

    def detach_volume(self, blockdevice_id):
        return self._osnexusApi.detachOsnexusvolume(blockdevice_id)

    def get_device_path(self, blockdevice_id):
        return self._osnexusApi.getOsNexusDevicePath(blockdevice_id)

def GetOsnexusStorageApi(ipaddress, username, password, gold_tier, silver_tier, bronze_tier, default_pool ):
    return OsnexusBlockDeviceAPI(ipaddress, username, password, gold_tier, silver_tier, bronze_tier, default_pool)
