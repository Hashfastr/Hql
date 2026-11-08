import maps.fields;

// product('windows').category('process_creation') -> Elastic
// product('windows').service('security')          -> Splunk
class windows = {
    let process_creation = database('elastic').index('logs-endpoint.events.process-*') | map ecs_proc;
    let security = database('splunk').index('wineventlog') | map splunk_sec;
};
