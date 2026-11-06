// Sigma logsources over Azure Monitor / Microsoft Sentinel tables. To point raw
// Sigma here, set the header in config/sigma.yml to: import maps.azure
//
// Only logsources with a table are defined, the rest fail with "No source resolved".
//
// The Kusto database evaluates every Hql operator locally, so each query pulls its
// whole result set. The time bound and table filters in the raw KQL are what keep
// that small. It also fixes the columns a map can't:
//   - Dynamic columns become strings, Sigma's string matching fails on objects and
//     arrays. A field inside one is then only reachable by contains.
//   - SigninLogs.ResultType becomes an int, as rules write it unquoted.
//   - SigninLogs.Status gets the Success rules compare it to, the column itself only
//     holds an error code and failure details.
import maps.azure_fields;

class azure = {
    let activitylogs = database('kusto').raw('AzureActivity | where TimeGenerated > ago(1d)') | map azure_activity;
    let auditlogs = database('kusto').raw('AuditLogs | where TimeGenerated > ago(1d) | extend TargetResources = tostring(TargetResources), InitiatedBy = tostring(InitiatedBy), AdditionalDetails = tostring(AdditionalDetails)') | map azure_audit;
    let signinlogs = database('kusto').raw("SigninLogs | where TimeGenerated > ago(1d) | extend Status = iff(ResultType == '0', 'Success', tostring(Status)), ResultType = toint(ResultType)") | map azure_signin;
    let riskdetection = database('kusto').raw('AADUserRiskEvents | where TimeGenerated > ago(1d)') | map azure_risk;
};

class windows = {
    let security = database('kusto').raw('SecurityEvent | where TimeGenerated > ago(1d)') | map azure_security_event;
    let process_creation = database('kusto').raw("DeviceProcessEvents | where TimeGenerated > ago(1d) and ActionType == 'ProcessCreated'") | map azure_device_process;
    let network_connection = database('kusto').raw('DeviceNetworkEvents | where TimeGenerated > ago(1d)') | map azure_device_network;
    let image_load = database('kusto').raw('DeviceImageLoadEvents | where TimeGenerated > ago(1d)') | map azure_device_image_load;
    let file_event = database('kusto').raw("DeviceFileEvents | where TimeGenerated > ago(1d) and ActionType == 'FileCreated'") | map azure_device_file;
    let file_change = database('kusto').raw("DeviceFileEvents | where TimeGenerated > ago(1d) and ActionType == 'FileModified'") | map azure_device_file;
    let file_delete = database('kusto').raw("DeviceFileEvents | where TimeGenerated > ago(1d) and ActionType == 'FileDeleted'") | map azure_device_file;
    let file_rename = database('kusto').raw("DeviceFileEvents | where TimeGenerated > ago(1d) and ActionType == 'FileRenamed'") | map azure_device_file;
    let registry_add = database('kusto').raw("DeviceRegistryEvents | where TimeGenerated > ago(1d) and ActionType == 'RegistryKeyCreated'") | map azure_device_registry;
    let registry_delete = database('kusto').raw("DeviceRegistryEvents | where TimeGenerated > ago(1d) and ActionType in ('RegistryKeyDeleted', 'RegistryValueDeleted')") | map azure_device_registry;
    let registry_set = database('kusto').raw("DeviceRegistryEvents | where TimeGenerated > ago(1d) and ActionType == 'RegistryValueSet'") | map azure_device_registry;
    let registry_event = database('kusto').raw('DeviceRegistryEvents | where TimeGenerated > ago(1d)') | map azure_device_registry;
};
