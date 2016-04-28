# Copyright 2016 OSNEXUS Corporation
# See LICENSE file for details.

from twisted.trial.unittest import SynchronousTestCase
from uuid import uuid4
from bitmath import Byte, GiB
from osnexus_flocker_driver import osnexusdriver
from flocker.node.agents.test.test_blockdevice import (
    make_iblockdeviceapi_tests, make_iprofiledblockdeviceapi_tests
)

def GetTestOsnexusStorage(test_case):
    osnexusClient = osnexusdriver.GetOsnexusStorageApi("10.0.11.9", "admin", "password", "my_gold_tier", "", "", "my_def_pool")
    test_case.addCleanup(osnexusClient._cleanup)
    return osnexusClient

class OsnexusBlockDeviceAPIInterfaceTests(
        make_iblockdeviceapi_tests(
            blockdevice_api_factory=(
                lambda test_case: GetTestOsnexusStorage(test_case)
            ),
            minimum_allocatable_size=int(GiB(8).to_Byte().value),
            device_allocation_unit=int(GiB(8).to_Byte().value),
            unknown_blockdevice_id_factory=lambda test: unicode(uuid4())
        )
):
    """
    Interface adherence Tests for ``OsnexusBlockDeviceAPI``
    """

class OsnexusProfiledBlockDeviceAPIInterfaceTests(
        make_iprofiledblockdeviceapi_tests(
            profiled_blockdevice_api_factory=(
                lambda test_case: GetTestOsnexusStorage(test_case)
            ),
            dataset_size=int(GiB(1).to_Byte().value)
        )
):
        """
        Interface adherence tests for ``IProfiledBlockDeviceAPI``.
        """

class OsnexusBlockDeviceAPIImplementationTests(SynchronousTestCase):
    """
    Implementation specific tests for ``OsnexusBlockDeviceAPI``.
    """
    def test_osnexus_api(self):
        pass
