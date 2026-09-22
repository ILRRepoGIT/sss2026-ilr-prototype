// Role assignments that let the build VM's managed identity
// read the dataset, write evidence/staging, and read the link secret
// (provisioning guide §6). Deploy into the PERSISTENT resource group with the
// principalId and subnetId outputs of build-vm.bicep:
//   az deployment group create -g rg-sss2026-ilr -f infra/build-vm-roles.bicep -p principalId=<id>

targetScope = 'resourceGroup'

param dataAccountName string = 'stsss2026ilrdata'
param webAccountName string = 'stsss2026ilrweb'
param keyVaultName string = 'kv-sss2026-ilr'
param frontDoorName string = 'afd-sss2026-ilr'
@description('Object id of the build VM managed identity.')
param principalId string
@description('Give the VM identity write access to $web (publisher role). Set false once a separate publisher identity exists.')
param vmIsPublisher bool = true

// Storage Blob Data Reader / Contributor, Key Vault Secrets User
var reader = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '2a2b9908-6ea1-4ae2-8e65-a410df84e7d1')
var contributor = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
var secretsUser = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6')
// CDN Profile Contributor (Front Door purge on activation / withdrawal)
var cdnContributor = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ec156ff8-a8d1-4d15-830c-5b80698ca432')

resource dataAccount 'Microsoft.Storage/storageAccounts@2023-05-01' existing = { name: dataAccountName }
resource webAccount 'Microsoft.Storage/storageAccounts@2023-05-01' existing = { name: webAccountName }
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' existing = { name: keyVaultName }
resource afd 'Microsoft.Cdn/profiles@2024-02-01' existing = { name: frontDoorName }

resource dataBlob 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' existing = { parent: dataAccount, name: 'default' }
resource webBlob 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' existing = { parent: webAccount, name: 'default' }

resource cDataset 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' existing = { parent: dataBlob, name: 'dataset' }
resource cRegister 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' existing = { parent: dataBlob, name: 'register' }
resource cEvidence 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' existing = { parent: dataBlob, name: 'evidence' }
resource cLedger 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' existing = { parent: dataBlob, name: 'ledger' }
resource cStaging 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' existing = { parent: webBlob, name: 'staging' }
resource cWeb 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' existing = { parent: webBlob, name: '$web' }

resource raDataset 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(cDataset.id, principalId, 'reader')
  scope: cDataset
  properties: { principalId: principalId, principalType: 'ServicePrincipal', roleDefinitionId: reader }
}
resource raRegister 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(cRegister.id, principalId, 'contributor')
  scope: cRegister
  properties: { principalId: principalId, principalType: 'ServicePrincipal', roleDefinitionId: contributor }
}
resource raEvidence 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(cEvidence.id, principalId, 'contributor')
  scope: cEvidence
  properties: { principalId: principalId, principalType: 'ServicePrincipal', roleDefinitionId: contributor }
}
resource raLedger 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(cLedger.id, principalId, 'contributor')
  scope: cLedger
  properties: { principalId: principalId, principalType: 'ServicePrincipal', roleDefinitionId: contributor }
}
resource raStaging 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(cStaging.id, principalId, 'contributor')
  scope: cStaging
  properties: { principalId: principalId, principalType: 'ServicePrincipal', roleDefinitionId: contributor }
}
resource raWeb 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (vmIsPublisher) {
  name: guid(cWeb.id, principalId, 'contributor')
  scope: cWeb
  properties: { principalId: principalId, principalType: 'ServicePrincipal', roleDefinitionId: contributor }
}
resource raPurge 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (vmIsPublisher) {
  name: guid(afd.id, principalId, 'cdn-contributor')
  scope: afd
  properties: { principalId: principalId, principalType: 'ServicePrincipal', roleDefinitionId: cdnContributor }
}
resource raSecret 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, principalId, 'secrets-user')
  scope: keyVault
  properties: { principalId: principalId, principalType: 'ServicePrincipal', roleDefinitionId: secretsUser }
}

// Network rules (the build subnet through the two storage firewalls and the key
// vault) are data-plane-adjacent settings on existing resources; deploy.sh applies
// them with the CLI:
//   az storage account network-rule add --account-name <data> -g <rg> --subnet <subnetId>
//   az storage account network-rule add --account-name <web>  -g <rg> --subnet <subnetId>
//   az keyvault network-rule add --name <kv> --subnet <subnetId>
