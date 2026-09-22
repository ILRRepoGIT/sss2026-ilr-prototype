// SSS2026 Interactive Learning Reports — persistent estate (provisioning guide §§3–5, 7).
// Deploy into the existing resource group (SSS2026_Interactive_Learning_reports):
//   az deployment group create -g SSS2026_Interactive_Learning_reports -f infra/main.bicep -p custodianObjectId=<id> adminIp=<ip>   (or run infra/deploy.sh, which passes the parameters)
// The build VM is a separate template (infra/build-vm.bicep) in its own resource group.

targetScope = 'resourceGroup'

@description('Azure region for every resource (UK data residency).')
param location string = 'uksouth'

@minLength(3)
@maxLength(24)
@description('Private data storage account: dataset, register, evidence, ledger. Never public.')
param dataAccountName string = 'stsss2026ilrdata'

@minLength(3)
@maxLength(24)
@description('Web origin storage account: static website ($web) and the private staging container.')
param webAccountName string = 'stsss2026ilrweb'

@description('Key Vault holding the link-token secret.')
param keyVaultName string = 'kv-sss2026-ilr'

@description('Front Door profile name.')
param frontDoorName string = 'afd-sss2026-ilr'

@description('Front Door endpoint name (the azurefd.net label).')
param endpointName string = 'sss2026-reports'

@allowed(['Premium_AzureFrontDoor', 'Standard_AzureFrontDoor'])
@description('Premium connects to the origin over Private Link (recommended). Standard reaches the public origin endpoint and needs infra/afd-origin-ip-rules.sh.')
param frontDoorSku string = 'Premium_AzureFrontDoor'

@description('Custom domain for the reports (e.g. reports.example.wales). Leave empty to add later.')
param customDomainHost string = ''

@description('Log Analytics workspace name.')
param logAnalyticsName string = 'law-sss2026-ilr'

@description('Object id of the report owner / secret custodian to be given Key Vault Secrets Officer. Leave empty to skip.')
param custodianObjectId string = ''

var tags = { project: 'SSS2026-ILR', owner: 'Industryline' }
var usePrivateLink = frontDoorSku == 'Premium_AzureFrontDoor'

// ---------------------------------------------------------------- storage: data
resource dataAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: dataAccountName
  location: location
  tags: tags
  kind: 'StorageV2'
  sku: { name: 'Standard_ZRS' }
  properties: {
    accessTier: 'Hot'
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false
    publicNetworkAccess: 'Enabled'
    networkAcls: { defaultAction: 'Deny', bypass: 'AzureServices' }
  }
}
resource dataBlob 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: dataAccount
  name: 'default'
  properties: {
    isVersioningEnabled: true
    deleteRetentionPolicy: { enabled: true, days: 30 }
    containerDeleteRetentionPolicy: { enabled: true, days: 30 }
  }
}
resource dataContainers 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = [for c in ['dataset', 'register', 'evidence', 'ledger']: {
  parent: dataBlob
  name: c
  properties: { publicAccess: 'None' }
}]

// ---------------------------------------------------------------- storage: web origin
resource webAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: webAccountName
  location: location
  tags: tags
  kind: 'StorageV2'
  sku: { name: 'Standard_ZRS' }
  properties: {
    accessTier: 'Hot'
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false
    publicNetworkAccess: 'Enabled'
    // default Allow at creation so the static-website feature and first uploads work;
    // deploy.sh switches the default action to Deny once Front Door's private endpoint
    // is approved and the build subnet rule is in place (guide §5.3, §6).
    networkAcls: { defaultAction: 'Allow', bypass: 'AzureServices' }
  }
}
resource webBlob 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: webAccount
  name: 'default'
  properties: {
    isVersioningEnabled: true
    deleteRetentionPolicy: { enabled: true, days: 14 }
  }
}
resource stagingContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: webBlob
  name: 'staging'
  properties: { publicAccess: 'None' }
}
// NOTE: static-website hosting ($web, index/404 documents) is a data-plane setting that
// ARM cannot switch on; deploy.sh runs `az storage blob service-properties update --static-website`.

// ---------------------------------------------------------------- key vault
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  tags: tags
  properties: {
    tenantId: subscription().tenantId
    sku: { family: 'A', name: 'standard' }
    enableRbacAuthorization: true
    enablePurgeProtection: true
    softDeleteRetentionInDays: 90
    publicNetworkAccess: 'Enabled'
    networkAcls: { defaultAction: 'Deny', bypass: 'AzureServices' }
  }
}
// Key Vault Secrets Officer: b86a8fe4-44ce-4948-aee5-eccb2c155cd7
resource custodianRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(custodianObjectId)) {
  name: guid(keyVault.id, custodianObjectId, 'secrets-officer')
  scope: keyVault
  properties: {
    principalId: custodianObjectId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'b86a8fe4-44ce-4948-aee5-eccb2c155cd7')
  }
}

// ---------------------------------------------------------------- log analytics
resource law 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: logAnalyticsName
  location: location
  tags: tags
  properties: { sku: { name: 'PerGB2018' }, retentionInDays: 90 }
}

// ---------------------------------------------------------------- front door
resource afd 'Microsoft.Cdn/profiles@2024-02-01' = {
  name: frontDoorName
  location: 'global'
  tags: tags
  sku: { name: frontDoorSku }
  properties: { originResponseTimeoutSeconds: 60 }
}
resource endpoint 'Microsoft.Cdn/profiles/afdEndpoints@2024-02-01' = {
  parent: afd
  name: endpointName
  location: 'global'
  properties: { enabledState: 'Enabled' }
}
resource originGroup 'Microsoft.Cdn/profiles/originGroups@2024-02-01' = {
  parent: afd
  name: 'og-reports'
  properties: {
    loadBalancingSettings: { sampleSize: 4, successfulSamplesRequired: 3, additionalLatencyInMilliseconds: 50 }
    healthProbeSettings: { probePath: '/health.txt', probeRequestType: 'HEAD', probeProtocol: 'Https', probeIntervalInSeconds: 120 }
    sessionAffinityState: 'Disabled'
  }
}
var webHost = replace(replace(webAccount.properties.primaryEndpoints.web, 'https://', ''), '/', '')
resource origin 'Microsoft.Cdn/profiles/originGroups/origins@2024-02-01' = {
  parent: originGroup
  name: 'origin-web'
  properties: {
    hostName: webHost
    originHostHeader: webHost
    httpPort: 80
    httpsPort: 443
    priority: 1
    weight: 1000
    enabledState: 'Enabled'
    enforceCertificateNameCheck: true
    sharedPrivateLinkResource: usePrivateLink ? {
      privateLink: { id: webAccount.id }
      groupId: 'web'
      privateLinkLocation: location
      requestMessage: 'SSS2026 ILR reports origin'
    } : null
  }
}

resource ruleSet 'Microsoft.Cdn/profiles/ruleSets@2024-02-01' = {
  parent: afd
  name: 'sss2026reports'
}
var csp = 'default-src \'none\'; script-src \'self\'; style-src \'self\' \'unsafe-inline\'; img-src \'self\' data:; font-src \'self\' data:; connect-src \'self\'; base-uri \'none\'; frame-ancestors \'none\'; form-action \'none\''
resource ruleHeaders 'Microsoft.Cdn/profiles/ruleSets/rules@2024-02-01' = {
  parent: ruleSet
  name: 'noindexsecurity'
  properties: {
    order: 1
    matchProcessingBehavior: 'Continue'
    conditions: []
    actions: [
      { name: 'ModifyResponseHeader', parameters: { typeName: 'DeliveryRuleHeaderActionParameters', headerAction: 'Overwrite', headerName: 'X-Robots-Tag', value: 'noindex, nofollow, noarchive' } }
      { name: 'ModifyResponseHeader', parameters: { typeName: 'DeliveryRuleHeaderActionParameters', headerAction: 'Overwrite', headerName: 'X-Content-Type-Options', value: 'nosniff' } }
      { name: 'ModifyResponseHeader', parameters: { typeName: 'DeliveryRuleHeaderActionParameters', headerAction: 'Overwrite', headerName: 'Referrer-Policy', value: 'no-referrer' } }
      { name: 'ModifyResponseHeader', parameters: { typeName: 'DeliveryRuleHeaderActionParameters', headerAction: 'Overwrite', headerName: 'Strict-Transport-Security', value: 'max-age=31536000; includeSubDomains' } }
      { name: 'ModifyResponseHeader', parameters: { typeName: 'DeliveryRuleHeaderActionParameters', headerAction: 'Overwrite', headerName: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()' } }
      { name: 'ModifyResponseHeader', parameters: { typeName: 'DeliveryRuleHeaderActionParameters', headerAction: 'Overwrite', headerName: 'Content-Security-Policy', value: csp } }
    ]
  }
}
resource ruleImmutable 'Microsoft.Cdn/profiles/ruleSets/rules@2024-02-01' = {
  parent: ruleSet
  name: 'immutablerelease'
  dependsOn: [ruleHeaders]
  properties: {
    order: 2
    matchProcessingBehavior: 'Continue'
    conditions: [
      { name: 'UrlPath', parameters: { typeName: 'DeliveryRuleUrlPathMatchConditionParameters', operator: 'BeginsWith', matchValues: ['/r/'], negateCondition: false, transforms: [] } }
    ]
    actions: [
      { name: 'RouteConfigurationOverride', parameters: { typeName: 'DeliveryRuleRouteConfigurationOverrideActionParameters', cacheConfiguration: { queryStringCachingBehavior: 'IgnoreQueryString', isCompressionEnabled: 'Enabled', cacheBehavior: 'OverrideAlways', cacheDuration: '365.00:00:00' } } }
      { name: 'ModifyResponseHeader', parameters: { typeName: 'DeliveryRuleHeaderActionParameters', headerAction: 'Overwrite', headerName: 'Cache-Control', value: 'public, max-age=31536000, immutable' } }
    ]
  }
}
resource ruleEntry 'Microsoft.Cdn/profiles/ruleSets/rules@2024-02-01' = {
  parent: ruleSet
  name: 'entryrevalidate'
  dependsOn: [ruleImmutable]
  properties: {
    order: 3
    matchProcessingBehavior: 'Continue'
    conditions: [
      { name: 'UrlPath', parameters: { typeName: 'DeliveryRuleUrlPathMatchConditionParameters', operator: 'BeginsWith', matchValues: ['/2026/'], negateCondition: false, transforms: [] } }
    ]
    actions: [
      { name: 'RouteConfigurationOverride', parameters: { typeName: 'DeliveryRuleRouteConfigurationOverrideActionParameters', cacheConfiguration: { queryStringCachingBehavior: 'IgnoreQueryString', isCompressionEnabled: 'Enabled', cacheBehavior: 'OverrideAlways', cacheDuration: '00:01:00' } } }
      { name: 'ModifyResponseHeader', parameters: { typeName: 'DeliveryRuleHeaderActionParameters', headerAction: 'Overwrite', headerName: 'Cache-Control', value: 'no-cache, must-revalidate' } }
    ]
  }
}

resource customDomain 'Microsoft.Cdn/profiles/customDomains@2024-02-01' = if (!empty(customDomainHost)) {
  parent: afd
  name: 'reports-domain'
  properties: {
    hostName: customDomainHost
    tlsSettings: { certificateType: 'ManagedCertificate', minimumTlsVersion: 'TLS12' }
  }
}

resource route 'Microsoft.Cdn/profiles/afdEndpoints/routes@2024-02-01' = {
  parent: endpoint
  name: 'route-reports'
  dependsOn: [origin, ruleEntry]
  properties: {
    originGroup: { id: originGroup.id }
    ruleSets: [ { id: ruleSet.id } ]
    supportedProtocols: ['Http', 'Https']
    patternsToMatch: ['/*']
    forwardingProtocol: 'HttpsOnly'
    linkToDefaultDomain: empty(customDomainHost) ? 'Enabled' : 'Disabled'
    httpsRedirect: 'Enabled'
    enabledState: 'Enabled'
    customDomains: empty(customDomainHost) ? [] : [ { id: customDomain.id } ]
    cacheConfiguration: {
      queryStringCachingBehavior: 'IgnoreQueryString'
      compressionSettings: {
        isCompressionEnabled: true
        contentTypesToCompress: ['application/json', 'text/html', 'text/css', 'application/javascript', 'text/javascript', 'image/svg+xml', 'text/plain']
      }
    }
  }
}

resource afdDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'afd-logs'
  scope: afd
  properties: {
    workspaceId: law.id
    logs: [
      { category: 'FrontDoorAccessLog', enabled: true }
      { category: 'FrontDoorHealthProbeLog', enabled: true }
    ]
    metrics: [ { category: 'AllMetrics', enabled: true } ]
  }
}

output dataAccountId string = dataAccount.id
output webAccountId string = webAccount.id
output webEndpoint string = webAccount.properties.primaryEndpoints.web
output keyVaultId string = keyVault.id
output frontDoorEndpointHost string = endpoint.properties.hostName
output customDomainValidation object = empty(customDomainHost) ? {} : customDomain!.properties.validationProperties
output logAnalyticsId string = law.id
