import maps.fields;

// product('windows').category('process_creation') -> Elastic
// product('windows').service('security')          -> Splunk
class windows = {
    let process_creation = database('fake-elastic').file('windows-process.ndjson') | map ecs_proc;
    let security = database('fake-splunk').file('windows-security.ndjson') | map splunk_sec;
};
