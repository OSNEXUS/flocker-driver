# OSNEXUS QuantaStor plugin for ClusterHQ/Flocker
Flocker storage driver for Quantastor from OSNEXUS
ClusterHQ/Flocker provides an easy way for Docker containers to persist data. OSNEXUS QuantaStor plugin for Flocker provides fast, local and persistent data for Docker containers.

# Description
QuantaStor is a unified Software Defined Storage (SDS) platform designed to scale up and out to make storage management easy while reducing overall enterprise storage costs. 
More information about Quantastor can be found at (http://www.osnexus.com/storage-appliance-os)

OSNEXUS QuantaStor plugin also supports Flocker Storage profiles (Gold, Silver and Bronze).
Details regarding Flocker Storage Profiles can be found on the ClusterHQ site at -
https://docs.clusterhq.com/en/latest/flocker-features/storage-profiles.html#storage-profiles 
TODO : Add a link to storage Tiers

# Supported platforms
* Ubuntu 14.04

# Prerequisites
* Requires existing Flocker installation.
* Requires isciadm. To configure the flocker nodes as iSCSI initiator install the open-iscsi package
```
sudo apt-get install open-iscsi
```
Flocker must already be installed before installing this plugin. For details on installing Flocker please visit the ClusterHQ site at (https://docs.clusterhq.com/en/latest/)

# Installation

Install using python
```bash
git clone https://github.com/OSNEXUS/flocker-driver
cd osnexus-flocker-driver/
sudo /opt/flocker/bin/python setup.py install
```
**_Be sure to use /opt/flocker/bin/python to install the driver into the right python environment_**


Install using pip
```
git clone https://github.com/OSNEXUS/flocker-driver
cd osnexus-flocker-driver/
/opt/flocker/bin/pip install -e .
```
**_Be sure to use /opt/flocker/bin/pip to install the driver into the right python environment_**

Verify that the plugin is installed correctly:
```bash
pip list | grep -i osnexus
osnexus-flocker-driver (1.0)
```

# Usage
Configure the plugin for Flocker by adding the following configuration to the file `/etc/flocker/agent.yml`:
```bash
    "dataset":
        backend: osnexus_flocker_driver
        ipaddress: "10.0.11.9" 
        password: password
        username: admin
        gold_tier: ""
        silver_tier: ""
        bronze_tier: "your_bronze_tier"
        default_pool: "your_default_pool"
```

**_This is an example configuration and needs to be edited to match your environment configuration._**
* Adjust the `ipaddress`, `username`, and `password` values to match those of the QuantaStor storage system.
* Define the Storage Tier names for the `gold_tier`, `silver_tier`, and `bronze_tier` storage profiles.
* Adjust the `default_pool` value to match the QuantaStorage storage pool.

**_If these values are left empty, the OSNEXUS QuantaStor plugin will the use the default values:
`flocker_def_gold_tier`, `flocker_def_silver_tier`, `flocker_def_bronze_tier`, `flocker_def_pool`_**


# Configure the Quantastor system for Flocker
QuantaStor supports the use of REST APIs for development of applications and extensions to remotely manage QuantaStor storage systems.
Make sure the flocker nodes can communicate with the Quantastor system. 
Confirm communication with the QuantaStor system using a RESTful API call to enumerate the storage system:
```
curl -u admin:password https://10.0.11.9:8153/qstorapi/storageSystemGet -k
```
This command should return information about the Quantastor system. Confirm all the flocker nodes are able to communicate with the Quantastor system. 

OSNEXUS Quantastor plugin for Flocker supports storage profiles (GOLD, SILVER and BRONZE). 

Before any volumes can be provisioned by Flocker, Quantastor needs to be configured with storage pools and/or storage tiers. 
This can be done from the Quantastor Web interface or from the Quantastor CLI. 

Example, http://10.0.11.9 will access the Web interface for the Quantastor system on the IP address 10.0.11.9.

Confirm that Storage Tier names for each profile and the default pool name have been configured in the agent.yml file.  If empty, note that the default names will be used: `flocker_def_gold_tier`, `flocker_def_silver_tier`, `flocker_def_bronze_tier`, `flocker_def_pool`

Quantastor needs to be configured with the storage pools and/or storage tiers specified in the agent.yml.  The following examples will use the default names shown above.  Adjust to reflect the values configured in the agent.yml file.

```
qs pool-create --name flocker_def_pool --disk-list=sdb --raid-type=LINEAR, --pool-type=zfs, --desc="A default pool for flocker" 
```
More information on the storage pools can be found at (http://wiki.osnexus.com/index.php?title=QuantaStor_Administrators_Guide#Managing_Storage_Pools)


To create a volume with a particular storage profile, create the following Storage Tiers in Quantastor - flocker_gold_pool, flocker_silver_pool and flocker_bronze_pool.
Quantastor supports creation of a grid with multiple Quantastor systems in a grid. Each Quantastor system in the grid is called a node. Storage Tier can span multiple nodes. 
More information on Storage Tiers can be found here - http://wiki.osnexus.com/index.php?title=QuantaStor_Administrators_Guide#Managing_Storage_Provisioning_Tiers_.28Storage_Pool_Groups.29

To create the Storage Tiers follow these steps
* Create storage pool (flocker_gold_pool)
```
qs pool-create --name flocker_gold_pool --disk-list=sdb --raid-type=LINEAR, --pool-type=zfs, --desc="A pool for flocker gold profile" --compress=true
```
* If you want multiple pools in a tier, create multiple pools (flocker_gold_pool1, flocker_gold_pool2, flocker_gold_pool3)
```
qs pool-create --name flocker_gold_pool1 --disk-list=sdb --raid-type=LINEAR, --pool-type=zfs, --desc="A pool for flocker gold profile" --compress=true
qs pool-create --name flocker_gold_pool2 --disk-list=sdc --raid-type=LINEAR, --pool-type=zfs, --desc="A pool for flocker gold profile" --compress=true
qs pool-create --name flocker_gold_pool3 --disk-list=sdd --raid-type=LINEAR, --pool-type=zfs, --desc="A pool for flocker gold profile" --compress=true
```

* Create a storage Tier from the created storage pools
```
qs storage-tier-create --name="flocker_gold_tier" --pool-list=flocker_gold_pool --desc="For Flocker gold profile" --storage-class="High-Performance" --storage-type=SSD
```
```
qs storage-tier-create --name="flocker_gold_tier" --pool-list=flocker_gold_pool1,flocker_gold_pool2,flocker_gold_pool3 --desc="For Flocker gold profile" --storage-class="High-Performance" --storage-type=SSD
```
```
qs storage-tier-create --name="flocker_bronze_tier" --pool-list=flocker_gold_pool --desc="For Flocker bronze profile" --storage-class="Backup/Archive" --storage-type=SATA
```
**_The following names are case sensitive - flocker_gold_tier, flocker_silver_tier, flocker_bronze_tier and flocker_def_pool_**

**_Please select the storage pool options to best fit for each storage profile_**

More information about Flocker storage profiles can be found at -
https://docs.clusterhq.com/en/latest/flocker-features/storage-profiles.html#storage-profiles

# Running Tests
After having the agent.yml in place, tests can be performed on the OSNEXUS Quantastor plugin for Flocker. Use the following command to run the tests on the Flocker nodes.
```
trial osnexus_flocker_driver.test_osnexus

```
The output should be as below 
```
Ran 30 tests in 425.276s

PASSED (successes=30)
```

# Demo
Coming soon

# Support
Please file bugs and issues at the Github issues page. For more general discussions you can contact the Flocker team at Google Groups. Please contact OSNEXUS support (support@osnexus.com) for any issues.

