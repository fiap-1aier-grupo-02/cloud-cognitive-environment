@description('Região dos recursos. Default: a do Resource Group.')
param location string = resourceGroup().location

@description('Usuário administrador da VM.')
param adminUsername string = 'azureuser'

@description('Conteúdo da chave pública SSH (cat ~/.ssh/id_rsa.pub).')
@secure()
param adminPublicKey string

@description('IP público autorizado a abrir SSH (curl -s ifconfig.me).')
param meuIp string

@description('Tamanho da VM.')
param vmSize string = 'Standard_D2s_v3'

resource vnet 'Microsoft.Network/virtualNetworks@2023-09-01' = {
  name: 'vm-lab-aula01-vnet'
  location: location
  properties: {
    addressSpace: {
      addressPrefixes: [ '10.0.0.0/16' ]
    }
    subnets: [
      {
        name: 'default'
        properties: { addressPrefix: '10.0.0.0/24' }
      }
      {
        name: 'subnet-app' // [3.1 - item 2] subnet da futura camada de aplicação
        properties: { addressPrefix: '10.0.2.0/24' }
      }
    ]
  }
}

resource nsg 'Microsoft.Network/networkSecurityGroups@2023-09-01' = {
  name: 'vm-lab-aula01-nsg'
  location: location
  properties: {
    securityRules: [
      {
        name: 'SSH'
        properties: {
          priority: 300
          direction: 'Inbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '22'
          sourceAddressPrefix: '${meuIp}/32' // [3.1 - item 1] antes era "*"
          destinationAddressPrefix: '*'
        }
      }
      {
        name: 'HTTPS'
        properties: {
          priority: 320
          direction: 'Inbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '443'
          sourceAddressPrefix: '*'
          destinationAddressPrefix: '*'
        }
      }
      {
        name: 'HTTP'
        properties: {
          priority: 340
          direction: 'Inbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '80'
          sourceAddressPrefix: '*'
          destinationAddressPrefix: '*'
        }
      }
    ]
  }
}

resource pip 'Microsoft.Network/publicIPAddresses@2023-09-01' = {
  name: 'vm-lab-aula01-ip'
  location: location
  sku: { name: 'Standard' }
  properties: { publicIPAllocationMethod: 'Static' }
}

resource nic 'Microsoft.Network/networkInterfaces@2023-09-01' = {
  name: 'vm-lab-aula01-nic'
  location: location
  properties: {
    enableAcceleratedNetworking: true
    networkSecurityGroup: { id: nsg.id }
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
  name: 'vm-lab-aula01'
  location: location
  properties: {
    hardwareProfile: { vmSize: vmSize }
    osProfile: {
      computerName: 'vm-lab-aula01'
      adminUsername: adminUsername
      linuxConfiguration: {
        disablePasswordAuthentication: true
        ssh: {
          publicKeys: [
            {
              path: '/home/${adminUsername}/.ssh/authorized_keys'
              keyData: adminPublicKey
            }
          ]
        }
      }
    }
    storageProfile: {
      imageReference: {
        publisher: 'canonical'
        offer: 'ubuntu-24_04-lts'
        sku: 'server'
        version: 'latest'
      }
      osDisk: {
        createOption: 'FromImage'
        caching: 'ReadWrite'
        managedDisk: { storageAccountType: 'Premium_LRS' }
      }
    }
    networkProfile: {
      networkInterfaces: [ { id: nic.id } ]
    }
    diagnosticsProfile: {
      bootDiagnostics: { enabled: true }
    }
  }
}

output publicIpId string = pip.id
output vmName string = vm.name
output appSubnetId string = vnet.properties.subnets[1].id