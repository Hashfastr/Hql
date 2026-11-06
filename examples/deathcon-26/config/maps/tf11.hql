// TF11 datasets as Sigma logsources:
//   import maps.tf11;
//   product('windows').category('process_access') | where GrantedAccess == '0x1400'
// Only logsources that have data are defined, the rest fail with
// "No source resolved".
import maps.tf11_fields;

let tf11_beats = database('json').http('tf11-so-beats-large.json');
let tf11_network = database('json').http('tf11-so-network.json');
let tf11_sysmon_events = tf11_beats | where winlog.channel == 'Microsoft-Windows-Sysmon/Operational';

class windows = {
    let process_creation = tf11_sysmon_events | where winlog.event_id == '1' | map tf11_sysmon;
    let network_connection = tf11_sysmon_events | where winlog.event_id == '3' | map tf11_sysmon;
    let image_load = tf11_sysmon_events | where winlog.event_id == '7' | map tf11_sysmon;
    let raw_access_thread = tf11_sysmon_events | where winlog.event_id == '9' | map tf11_sysmon;
    let process_access = tf11_sysmon_events | where winlog.event_id == '10' | map tf11_sysmon;
    let file_event = tf11_sysmon_events | where winlog.event_id == '11' | map tf11_sysmon;
    let registry_add = tf11_sysmon_events | where winlog.event_id == '12' and winlog.event_data.EventType == 'CreateKey' | map tf11_sysmon;
    let registry_delete = tf11_sysmon_events | where winlog.event_id == '12' and winlog.event_data.EventType in ('DeleteKey', 'DeleteValue') | map tf11_sysmon;
    let registry_set = tf11_sysmon_events | where winlog.event_id == '13' | map tf11_sysmon;
    let registry_event = tf11_sysmon_events | where winlog.event_id in ('12', '13', '14') | map tf11_sysmon;
    let pipe_created = tf11_sysmon_events | where winlog.event_id in ('17', '18') | map tf11_sysmon;
    let dns_query = tf11_sysmon_events | where winlog.event_id == '22' | map tf11_sysmon;
    let file_delete = tf11_sysmon_events | where winlog.event_id in ('23', '26') | map tf11_sysmon;
    let security = tf11_beats | where winlog.channel == 'Security' | map tf11_security;
    let file_change = tf11_sysmon_events | where winlog.event_id == '2' | map tf11_sysmon;
    let process_termination = tf11_sysmon_events | where winlog.event_id == '5' | map tf11_sysmon;
    let sysmon = tf11_sysmon_events | map tf11_sysmon;
    let application = tf11_beats | where winlog.channel == 'Application' | map tf11_security;
};

class zeek = {
    let dns = tf11_network | where _source.event.module == 'zeek' and _source.event.dataset == 'dns' | map tf11_zeek;
    let http = tf11_network | where _source.event.module == 'zeek' and _source.event.dataset == 'http' | map tf11_zeek;
    let x509 = tf11_network | where _source.event.module == 'zeek' and _source.event.dataset == 'x509' | map tf11_zeek;
};
