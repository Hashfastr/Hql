/**
 * @title AzureHound Sign-in
 * @id 274e3ee2-98b6-47ab-ad1e-f70fe18af856
 * @author DEATHCon 2026 (HaC)
 * 
 * @status experimental
 * @level high
 * @schedule 0,15,30,45 * * * *
 * @description
 * AzureHound collects Entra ID objects and permissions for BloodHound attack
 * path analysis, and signs in with its own user agent unless it's changed.
 * 
 * @tags
 * - attack.discovery
 * - attack.t1087.004
 * 
 * @triage
 * Check whether the account belongs to a red team or an approved BloodHound
 * assessment. Otherwise treat the account as compromised: review its other
 * sign-ins from the same IP address and reset its credentials.
 * 
 * @references
 * - https://github.com/SpecterOps/AzureHound
 * 
 * @changelog
 * - 2026-11-07 Created
 */
import maps.azure;
product('azure').service('signinlogs')
| where userAgent contains 'azurehound'
| project TimeGenerated, Username, IPAddress, userAgent, AppDisplayName, Status
