/**
 * @title Password Spray - Many Failed Sign-ins From One IP Address
 * @id c9813f9e-5f91-4945-9fe5-d2184d927600
 * @author DEATHCon 2026 (HaC)
 * 
 * @status experimental
 * @level medium
 * @schedule 0 * * * *
 * @description
 * A password spray tries a few common passwords against many accounts, so it
 * shows up as many failed sign-ins from one IP address. A single Sigma rule
 * matches events one at a time and can't count them; this does.
 * 
 * @tags
 * - attack.credential-access
 * - attack.t1110.003
 * 
 * @triage
 * Check whether the IP address is a known egress point, such as a VPN or a
 * proxy where many users fail at once. Otherwise look for a successful
 * sign-in from the same IP address to any of the listed accounts.
 * 
 * @references
 * - https://attack.mitre.org/techniques/T1110/003/
 * 
 * @changelog
 * - 2026-11-07 Created
 */
import maps.azure;

let threshold = 10;
product('azure').service('signinlogs')
| where ResultType != 0
| summarize Failures = count(), Users = make_list(Username) by IPAddress
| where Failures >= threshold
