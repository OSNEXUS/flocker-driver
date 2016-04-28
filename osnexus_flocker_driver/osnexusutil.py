# Copyright 2016 OSNEXUS Corporation
# See LICENSE file for details.

import requests
import json
from uuid import UUID
from requests.auth import HTTPBasicAuth
import socket
import time
import subprocess
import uuid
from twisted.python.filepath import FilePath

from flocker.node.agents.blockdevice import (
    AlreadyAttachedVolume, IBlockDeviceAPI, IProfiledBlockDeviceAPI,
    BlockDeviceVolume, UnknownVolume, UnattachedVolume
)

from qsclient import qsclient
from qsclient import Host
from qsclient import Pool

class VolumeProfiles():
    """
    :ivar GOLD: The profile for fast storage.
    :ivar SILVER: The profile for intermediate/default storage.
    :ivar BRONZE: The profile for cheap storage.
    :ivar DEFAULT: The default profile if none is specified.
    """
    PROFILE_GOLD = 'gold'
    PROFILE_SILVER = 'silver'
    PROFILE_BRONZE = 'bronze'
    PROFILE_DEFAULT = PROFILE_GOLD

    PROFILE_GOLD_TIER = 'flocker_def_gold_tier'
    PROFILE_SILVER_TIER = 'flocker_def_silver_tier'
    PROFILE_BRONZE_TIER = 'flocker_def_bronze_tier'
    PROFILE_DEFAULT_POOL = 'flocker_def_pool'


class osnexusAPI(object):

    def __init__(self, ipAddress, username, password, gold_tier, silver_tier, bronze_tier, default_pool, logger):
        self._qsclient = qsclient(ipAddress, username, password, logger)
        self._ipAddress = ipAddress
        self._hostIqn = ""
        self._osnexusHostId = ""
        self._osnexusDefPoolId = ""
        self._osnexusTierId = ""
        self._gold_tier = gold_tier
        self._silver_tier = silver_tier
        self._bronze_tier = bronze_tier
        self._default_pool = default_pool
        self._logger = logger

        if(gold_tier == ""):
            self._gold_tier = VolumeProfiles.PROFILE_GOLD_TIER

        if(silver_tier == ""):
            self._silver_tier = VolumeProfiles.PROFILE_SILVER_TIER

        if(bronze_tier == ""):
            self._bronze_tier = VolumeProfiles.PROFILE_BRONZE_TIER

        if(default_pool == ""):
            self._default_pool = VolumeProfiles.PROFILE_DEFAULT_POOL

    def listOsnexusVolumes(self):
        try:
            # volumes is the flocker data type
            volumes = []
            qs_vols = self._qsclient.list_volumes()

            for vol in qs_vols:
                #Add only the volumes starting with "flockerVol-"
                volUuid = self.getDataSetId(vol._name)
                if volUuid is None:
                    continue

                #Now get the host access list for this volume to figure out if it is attached
                if self.isVolumeAttached(vol._id) == True:
                    volumes.append(BlockDeviceVolume(
                        blockdevice_id=unicode(vol._id),
                        size=int(vol._size),
                        attached_to=unicode(socket.gethostbyname(socket.getfqdn())),
                        dataset_id=volUuid))
                else:
                    volumes.append(BlockDeviceVolume(
                        blockdevice_id=unicode(vol._id),
                        size=int(vol._size),
                        attached_to=None,
                        dataset_id=volUuid))
        except Exception as e:
            self._logger.error("List volume failed with exception")
            raise e
        return volumes

    # Flocker passes in dataset_id which is a UID. We use the dataset_id in the quantastor volume name along with "flockerVol-"
    # The internal object ID created by quantastor for this volume is used in the blockdevice_id
    # All other flocker entry points pass in the blockdevice_id, which can be directly used for making API calls on the volume.
    def createOsnexusVolume(self, dataset_id, size):
        try:
            if self._osnexusDefPoolId == "":
                def_pool = self._qsclient.get_pool(self._default_pool)
                self._osnexusDefPoolId = def_pool._id

            volName="flockerVol-{0}".format(dataset_id)
            # Check the pools and pass that to qsclient.create_volume
            vol = self._qsclient.create_volume(volName, size, "createdbyFlocker", self._osnexusDefPoolId)
            flocker_volume = BlockDeviceVolume(
                blockdevice_id=vol._id,
                size=vol._size,
                attached_to=None,
                dataset_id=dataset_id)
            return flocker_volume
        except Exception as e:
            self._logger.error("Create volume failed. Dataset Id '%s'", dataset_id)
            raise e

    def createOsnexusVolumeWithProfile(self, dataset_id, size, profile_name):
        try:
            tier = ""
            if profile_name == VolumeProfiles.PROFILE_GOLD:
                tier = self._gold_tier
            elif profile_name == VolumeProfiles.PROFILE_SILVER:
                tier = self._silver_tier
            elif profile_name == VolumeProfiles.PROFILE_BRONZE:
                tier = self._bronze_tier
            elif profile_name == VolumeProfiles.PROFILE_DEFAULT:
                return self.createOsnexusVolume(dataset_id, size)

            if self._osnexusTierId == "":
                tier = self._qsclient.get_tier(tier)
                self._osnexusTierId = tier._id

            volName="flockerVol-{0}".format(dataset_id)
            # Check the pools and pass that to qsclient.create_volume
            vol = self._qsclient.create_volume(volName, size, "createdbyFlocker", self._osnexusTierId)
            flocker_volume = BlockDeviceVolume(
                blockdevice_id=vol._id,
                size=vol._size,
                attached_to=None,
                dataset_id=dataset_id)
            return flocker_volume
        except Exception as e:
            self._logger.error("Create volume with profile failed. Dataset Id '%s'", dataset_id)
            raise e



    def deleteOsnexusVolume(self, blockdevice_id):
        try:
            vol = self.validateVolume(blockdevice_id)

            if self.isVolumeAttached(blockdevice_id) is True:
                try:
                    self.doIscsiLogout(vol._name)
                except Exception as e:
                    self._logger.error("failed to logout in deleteVolume. blockdevice id '%s'", blockdevice_id)
                    raise e
            self._qsclient.delete_volume(blockdevice_id)
        except Exception as e:
            self._logger.error("Delete volume failed. block device Id '%s'", blockdevice_id)
            raise e

    # This function returns the datasetId from the volume name
    def getDataSetId(self, volName):
        if volName.find("flockerVol-") != 0:
                return None
        volName = volName[11:]
        volUuid = UUID(volName)
        return volUuid

    def validateVolume(self, blockdevice_id):
        try:
            vol = self._qsclient.get_volume(blockdevice_id)
            volName =  vol._name
            if volName.find("flockerVol-") != 0:
                raise UnknownVolume(blockdevice_id)
            return vol
        except Exception as e:
            raise UnknownVolume(blockdevice_id)

    def isVolumeAttached(self, blockdevice_id):
        acl_list = self._qsclient.volume_acl_enum(blockdevice_id)
        if len(acl_list) == 0:
            return False
        found = False
        for acl in acl_list:
            if acl._volid == blockdevice_id and acl._hostid.find(self._osnexusHostId) != -1:
                found = True
                break
        return found

    def attachOsnexusVolume(self, blockdevice_id, attach_to):
        vol = self.validateVolume(blockdevice_id)
        volUuid = self.getDataSetId(vol._name)
        if volUuid is None:
            raise UnknownVolume(blockdevice_id)

        if self.isVolumeAttached(blockdevice_id) is True:
            raise AlreadyAttachedVolume(blockdevice_id)

        self.createHost()
        self._qsclient.volume_attach(blockdevice_id, self._osnexusHostId)

        try:
            self.doIscsiLogin(vol._name)
        except Exception as e:
            self._logger.error("failed to login")
            raise UnattachedVolume(blockdevice_id)

        return BlockDeviceVolume(
            blockdevice_id=blockdevice_id,
            size=int(vol._size),
            attached_to=attach_to,
            dataset_id=volUuid)

    def detachOsnexusvolume(self, blockdevice_id):
        vol = self.validateVolume(blockdevice_id)
        if self.isVolumeAttached(blockdevice_id) is False:
            raise UnattachedVolume(blockdevice_id)
        try:
            self.doIscsiLogout(vol._name)
        except Exception as e:
            self._logger.error("failed to logout")
            raise UnattachedVolume(blockdevice_id)

        self._qsclient.volume_dettach(blockdevice_id, self._osnexusHostId)

    def getOsNexusDevicePath(self, blockdevice_id):
        vol = self.validateVolume(blockdevice_id)
        if self.isVolumeAttached(blockdevice_id) is False:
            raise UnattachedVolume(blockdevice_id)

        targetIqn = self.iscsiDiscovery(vol._name)
        return self.getIscsiPath(targetIqn)

    def doIscsiLogin(self, volName):
        try:
            targetIqn = self.iscsiDiscovery(volName)
        except Exception as e:
            self._logger.error("Volume [" + volName + "] not found during discovery")
            raise UnattachedVolume(volName)
        self.iscsiLogin(targetIqn)

    def doIscsiLogout(self, volName):
        try:
            targetIqn = self.iscsiDiscovery(volName)
        except Exception as e:
            self._logger.error("Volume [" + volName + "] not found during discovery")
            raise UnattachedVolume(volName)
        self.iscsiLogout(targetIqn)

    # Does iscsi discovery and returns the target IQN for the specified volume
    def iscsiDiscovery(self, volName):
        time.sleep(2)
        cmd = "iscsiadm -m discovery -t st -p " + self._ipAddress
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        (output, err) = p.communicate()
        listOutput = output.split('\n')
        volFound = False
        for line in listOutput:
            if line.find(volName) != -1:
                #Found the volume during iscsi discovery
                splitline = line.split()
                return splitline[1]
        if volFound is False:
            raise Exception("Failed to discover volume")

    def iscsiLogin(self, targetIqn):
        cmd = "iscsiadm -m node -l -T " + targetIqn
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        (output, err) = p.communicate()
        if output.find("successful"):
            time.sleep(3)
            return self.getIscsiPath(targetIqn)
        else:
            raise Exception("Failed to do iscsi login to the volume")

    def iscsiLogout(self, targetIqn):
        #print "iscsiLogout " + targetIqn
        cmd = "iscsiadm -m node -u -T " + targetIqn
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        (output, err) = p.communicate()
        if output.find("successful"):
            time.sleep( 2 )
            return
        else:
            raise Exception("Failed to do iscsi logout to the volume")

    def getIscsiPath(self, targetIqn):
        #print "getIscsiPath " + targetIqn
        cmd = "ls /dev/disk/by-path/"
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        (output, err) = p.communicate()

        listOutput = output.split('\n')
        volFound = False
        for line in listOutput:
            if line.find(targetIqn) != -1:
                cmd = "readlink -f  /dev/disk/by-path/" + line
                p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
                (output, err) = p.communicate()
                if output.find("dev"):
                    return FilePath(output.strip())
                else:
                    self._logger.error("Failed to find path from readlink")
                    raise Exception("Failed to find path from readlink")
        if volFound == False:
            self._logger.error("Failed to find device-by-path")
            raise Exception("Failed to find device-by-path")

    # Read the host iscsi IQN from the local file '/etc/iscsi/initiatorname.iscsi'
    # If the IQN is found, it assigns it to self._hostIqn for later use. Once it is set, we don't have to read
    # the file again
    def readIscsiIqn(self):
        if self._hostIqn != "":
            return
        try:
            f = open('/etc/iscsi/initiatorname.iscsi')
        except IOError:
            self._logger.error("File /etc/iscsi/initiatorname.iscsi not found !!")
            raise Exception("File /etc/iscsi/initiatorname.iscsi not found !!")

        ## Find the line containing InitiatorName
        line = f.readline()
        while line:
            if line.startswith("InitiatorName="):
                line.strip()
                self._hostIqn = line.rsplit('=')[1]
                self._hostIqn.strip()
                break
            line = f.readline()
        f.close()

    #Create a host in quantastor. If a host with the flocker node local IQN exists in quantastor, then the ID of
    # that quantastor host is used for attach/dettach operations
    # TODO : Should we always check with quantastor if the host id is valid ??
    def createHost(self):
        #Check if a host with this iqn exists
        if self._osnexusHostId != "":
            return

        self.readIscsiIqn()
        if self._hostIqn == "":
            print "InitiatorName not found in the file /etc/iscsi/initiatorname.iscsi"
            #TODO : Error ?? Handle this
        else:
            print self._hostIqn

        try:
            host = self._qsclient.host_initiator_get(self._hostIqn)
            self._osnexusHostId = host._hostId
        except Exception as e:
            # Host initiator was not found. Create a new one
            #Formulate a host name
            hostName = "FlockerHost-" + uuid.uuid1().__str__()
            host = self._qsclient.create_host(hostName, self._hostIqn)
            self._osnexusHostId = host._hostId

