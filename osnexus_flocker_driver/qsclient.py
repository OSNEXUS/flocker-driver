# Copyright 2016 OSNEXUS Corporation
# See LICENSE file for details.


import requests
import json
import time
from requests.auth import HTTPBasicAuth

class qsclient(object):
    auth = None
    osnexusUrl = ""

    def __init__(self, ip_address, user_name, password, logger):
        self._auth=HTTPBasicAuth(user_name, password)
        self._base_url = "https://" + ip_address + ":8153/qstorapi/"
        self._logger = logger

    def make_call(self, api, payload):
        strURL = self._base_url + api
        r = requests.get(strURL,  params=payload, verify=False, auth=self.auth)
        if r.status_code != 200:
            self._logger.error("Quantastor request failed for api '%s'. Status code is '%s'", api, r.status_code)
            raise Exception("Failed to make a request '" + api + "' payload '" + payload + "' status code = " + r.status_code)
        jsonOutput = r.json()

        if isinstance(jsonOutput, dict) and jsonOutput.has_key("RestError") == True:
            self._logger.error("Quantastor request failed. Status code is '%s'", jsonOutput['RestError'])
            raise Exception("Failed to make a request '" + api + "' payload '" + str(payload) + "' RestError = " + jsonOutput['RestError'])
        return jsonOutput

    def wait_on_task(self, jsonOutput):
        if 'task' not in jsonOutput.keys():
            raise Exception("Task object not found in jsonOutput", )
        task = jsonOutput["task"]
        task_id = task["id"]

        i = 0
        while (True):
            i = i + 1
            payload = {'id': task_id}
            jsonOutput = self.make_call("taskGet", payload)
            if 'taskState' in jsonOutput.keys():
                taskState = jsonOutput["taskState"]
                if taskState == 5 or taskState == 4 or taskState == 3:
                    return jsonOutput["customId"]

            if (i == 10):
                break
            time.sleep(i*2)
        self._logger.error("task id '%s' did not complete", task_id)
        raise Exception("task '" + task_id + "' did not complere'")

    def create_host(self, hostName, hostIqn):
        payload = {'hostname': hostName, 'iqn': hostIqn, 'hostType': 3, 'flags': 1}
        jsonOutput = self.make_call("hostAdd", payload)
        customId = self.wait_on_task(jsonOutput)
        #customId is the id of the newly created host object
        return self.get_host(customId)

    def get_host(self, hostId):
        payload = {'host': hostId}
        jsonOutput = self.make_call("hostGet", payload)
        hostObj = jsonOutput['obj']
        host = Host(hostObj["id"])
        return host

    def host_initiator_get(self, hostIqn):
        payload = {'initiator' : hostIqn}
        jsonOutput = self.make_call("hostInitiatorGet", payload)
        if 'obj' in jsonOutput.keys():
            hostObj = jsonOutput["obj"]
            host = Host(hostObj["hostId"])
            return host

    def list_volumes(self):
        payload = {}
        jsonOutput = self.make_call('storageVolumeEnum', payload)
        volumes = []
        for line in jsonOutput:
            vol = Volume(line["name"], line["id"], line["size"])
            volumes.append(vol)
        return volumes

    def create_volume(self, name, size, description, provisionableId):
        payload = {'count' : 1,
                   'name' : name,
                   'description' : description,
                   'accessMode' : 0,
                   'flags' : 1,
                   'thinProvisioned' : True,
                   'size' : str(size),
                   'provisionableId' : provisionableId}
        jsonOutput = self.make_call('storageVolumeCreate', payload)
        customId = self.wait_on_task(jsonOutput)
        return self.get_volume(customId)


    # TODO: Make this async
    def delete_volume(self, id):
        #print "with sync call"
        payload = {'storageVolume' : id,
                   'flags' : 3}
        jsonOutput = self.make_call('storageVolumeDeleteEx', payload)
        customId = self.wait_on_task(jsonOutput)

    def get_volume(self, id):
        payload = {'storageVolume' : id}
        jsonOutput = self.make_call('storageVolumeGet', payload)
        vol = Volume(jsonOutput['name'], jsonOutput['id'], jsonOutput['size'])
        return vol

    def volume_acl_enum(self, volume):
        payload = {'storageVolume' : volume}
        jsonOutput = self.make_call("storageVolumeAclEnum", payload)

        acl_list = []
        if len(jsonOutput) != 0:
            for acl in jsonOutput:
                acl = VolumeAcl(volume, acl["hostId"])
                acl_list.append(acl)
        return acl_list

    # TODO: Make this async
    def volume_attach(self, id, host):
        payload = {'storageVolume' : id,
                   'modType' : 0,
                   'hostList' : host,
                   'flags' : 1}
        jsonOutput = self.make_call("storageVolumeAclAddRemove", payload)
        customId = self.wait_on_task(jsonOutput)

    def volume_dettach(self, id, host):
        payload = { 'storageVolume' : id,
                    'modType' : 1,
                    'hostList' : host,
                    'flags' : 1}
        jsonOutput = self.make_call("storageVolumeAclAddRemove", payload)
        customId = self.wait_on_task(jsonOutput)

    def get_pool(self, name):
        payload = {'storagePool' : name}
        jsonOutput = self.make_call('storagePoolGet', payload)
        pool = Pool(jsonOutput['name'], jsonOutput['id'])
        return pool

    def get_tier(self, name):
        payload = {'storageTier' : name}
        jsonOutput = self.make_call('storageTierGet', payload)
        if 'obj' in jsonOutput.keys():
            tierobj = jsonOutput["obj"]
            return Tier(tierobj['name'], tierobj['id'])

class Tier(object):
    def __init__(self, name, id):
        self._name = name
        self._id = id

class Pool(object):
    def __init__(self, name, id):
        self._name = name
        self._id = id

class VolumeAcl(object):
    def __init__(self, volid, hostid):
        self._volid = volid
        self._hostid = hostid

class Volume(object):
    def __init__(self, name, id, size):
        self._name = name
        self._id = id
        self._size = size

class Host(object):
    def __init__(self, hostId):
        self._hostId = hostId
