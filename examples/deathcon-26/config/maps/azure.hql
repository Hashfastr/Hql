// Sigma logsources over Azure Monitor / Microsoft Sentinel tables. To point raw
// Sigma here, set the header in config/sigma.yml to: import maps.azure
//
// Only logsources with a table are defined, the rest fail with "No source resolved".
//
// The tables, their Sigma field names and the database they're queried in are in
// maps/azure_fields.hql. Everything here and the Sigma where after it is pushed to
// the database, parts the Kusto compiler can't express are evaluated locally.
import maps.azure_fields;

class azure = {
    let activitylogs = azure_activity;
    let auditlogs = azure_audit;
    let signinlogs = azure_signin;
    let riskdetection = azure_risk;
};

class windows = {
    let security = azure_security_event;
    let process_creation = azure_device_process | where ActionType == 'ProcessCreated';
    let network_connection = azure_device_network;
    let image_load = azure_device_image_load;
    let file_event = azure_device_file | where ActionType == 'FileCreated';
    let file_change = azure_device_file | where ActionType == 'FileModified';
    let file_delete = azure_device_file | where ActionType == 'FileDeleted';
    let file_rename = azure_device_file | where ActionType == 'FileRenamed';
    let registry_add = azure_device_registry | where EventType == 'RegistryKeyCreated';
    let registry_delete = azure_device_registry | where EventType in ('RegistryKeyDeleted', 'RegistryValueDeleted');
    let registry_set = azure_device_registry | where EventType == 'RegistryValueSet';
    let registry_event = azure_device_registry;
};
