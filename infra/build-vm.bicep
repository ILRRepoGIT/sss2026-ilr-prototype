// SSS2026 Interactive Learning Reports — the build virtual machine (provisioning guide §6).
// Deploy into the existing resource group (SSS2026_Interactive_Learning_reports) — the VM and its network are deleted after the run:
//   az deployment group create -g SSS2026_Interactive_Learning_reports -f infra/build-vm.bicep \
//      -p adminPublicKey="$(cat ~/.ssh/id_ed25519.pub)" adminSourceIp=<your public ip>
// Role assignments on the storage accounts and the key vault live in the persistent
// resource group and are made by infra/build-vm-roles.bicep with this template's
// principalId output (deploy.sh does both).

targetScope = 'resourceGroup'

param location string = 'uksouth'
param vmName string = 'vm-sss2026-build'
@description('''VM size. The default is the Intel Dsv6 family, which is the family of the 64-vCPU quota approved
for the subscription in UK South (checked 23 Sep 2026: Standard Dsv6 Family = 64, Standard DASv5 Family = 0).
D64s_v6 has 64 vCPU and 256 GiB like the D64as_v5 the guide was first written for; either builds the reports the
same way. The v6 sizes support only the NVMe disk controller, so it is set from the size below.''')
@allowed(['Standard_D64s_v6', 'Standard_D32s_v6', 'Standard_D16s_v6', 'Standard_D64as_v5', 'Standard_D32as_v5', 'Standard_D16as_v5', 'Standard_D16s_v5', 'Standard_D8as_v5'])
param vmSize string = 'Standard_D64s_v6'
var nvme = endsWith(vmSize, '_v6')
param adminUsername string = 'ilrbuild'
@description('OpenSSH public key for the admin user.')
param adminPublicKey string
@description('Public IPv4 address allowed to SSH in (your own). Use Bastion instead if the organisation forbids public IPs.')
param adminSourceIp string
@description('Data disk size in GiB (report outputs, evidence, working files).')
param dataDiskGb int = 1024

var tags = { project: 'SSS2026-ILR', owner: 'Industryline', lifetime: 'temporary' }

resource nsg 'Microsoft.Network/networkSecurityGroups@2023-11-01' = {
  name: 'nsg-sss2026-build'
  location: location
  tags: tags
  properties: {
    securityRules: [
      {
        name: 'allow-ssh-admin'
        properties: { priority: 100, direction: 'Inbound', access: 'Allow', protocol: 'Tcp', sourceAddressPrefix: adminSourceIp, sourcePortRange: '*', destinationAddressPrefix: '*', destinationPortRange: '22' }
      }
    ]
  }
}
resource vnet 'Microsoft.Network/virtualNetworks@2023-11-01' = {
  name: 'vnet-sss2026-build'
  location: location
  tags: tags
  properties: {
    addressSpace: { addressPrefixes: ['10.40.0.0/24'] }
    subnets: [
      {
        name: 'snet-build'
        properties: {
          addressPrefix: '10.40.0.0/26'
          networkSecurityGroup: { id: nsg.id }
          serviceEndpoints: [ { service: 'Microsoft.Storage' }, { service: 'Microsoft.KeyVault' } ]
        }
      }
    ]
  }
}
resource pip 'Microsoft.Network/publicIPAddresses@2023-11-01' = {
  name: 'pip-sss2026-build'
  location: location
  tags: tags
  sku: { name: 'Standard' }
  properties: { publicIPAllocationMethod: 'Static', publicIPAddressVersion: 'IPv4' }
}
resource nic 'Microsoft.Network/networkInterfaces@2023-11-01' = {
  name: 'nic-sss2026-build'
  location: location
  tags: tags
  properties: {
    ipConfigurations: [
      {
        name: 'ipconfig1'
        properties: {
          subnet: { id: vnet.properties.subnets[0].id }
          privateIPAllocationMethod: 'Dynamic'
          publicIPAddress: { id: pip.id }
        }
      }
    ]
  }
}
resource vm 'Microsoft.Compute/virtualMachines@2024-03-01' = {
  name: vmName
  location: location
  tags: tags
  identity: { type: 'SystemAssigned' }
  properties: {
    hardwareProfile: { vmSize: vmSize }
    osProfile: {
      computerName: vmName
      adminUsername: adminUsername
      linuxConfiguration: {
        disablePasswordAuthentication: true
        ssh: { publicKeys: [ { path: '/home/${adminUsername}/.ssh/authorized_keys', keyData: adminPublicKey } ] }
      }
    }
    storageProfile: {
      diskControllerType: nvme ? 'NVMe' : 'SCSI'
      imageReference: { publisher: 'Canonical', offer: 'ubuntu-24_04-lts', sku: 'server', version: 'latest' }
      osDisk: { createOption: 'FromImage', diskSizeGB: 128, managedDisk: { storageAccountType: 'Premium_LRS' }, deleteOption: 'Delete' }
      dataDisks: [
        { lun: 0, createOption: 'Empty', diskSizeGB: dataDiskGb, caching: 'ReadWrite', managedDisk: { storageAccountType: 'Premium_LRS' }, deleteOption: 'Delete' }
      ]
    }
    networkProfile: { networkInterfaces: [ { id: nic.id, properties: { deleteOption: 'Delete' } } ] }
    securityProfile: { securityType: 'TrustedLaunch', uefiSettings: { secureBootEnabled: true, vTpmEnabled: true } }
  }
}

output principalId string = vm.identity.principalId
output subnetId string = vnet.properties.subnets[0].id
output publicIp string = pip.properties.ipAddress
