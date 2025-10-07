<#
.SYNOPSIS
Switches the DNS configuration between a Pi-hole DNS server and the default DNS.

.DESCRIPTION
The `Switch-DNS` function toggles the DNS server settings for the active network adapter.
If the current DNS server is set to the Pi-hole IP, it resets to the default (automatic DNS).
If not, it switches to the specified Pi-hole IP.

.PARAMETER PiHoleIP
The IP address of the Pi-hole DNS server. Defaults to "192.168.50.202".

.EXAMPLE
Switch-DNS
Switches the DNS to the Pi-hole server (192.168.50.202) or back to the default.

.EXAMPLE
Switch-DNS -PiHoleIP "192.168.50.200"
Switches the DNS to a custom Pi-hole server (192.168.50.200) or back to the default.

.EXAMPLE
Switch-DNS -WhatIf
Shows what changes would be made to DNS settings without applying them.
Example output:
Current DNS: 192.168.50.1 (Default Router)
Target DNS:  192.168.50.202 (Pi-hole)
Will change: All active network adapters

.NOTES
This script modifies the DNS configuration for the active network adapter and requires
elevated permissions to run.
#>

function Switch-DNS {
    [CmdletBinding(SupportsShouldProcess)]
    param (
        [string]$PiHoleIP = "192.168.50.202"
    )

    # Check for admin privileges
    if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
        Write-Error "This script requires administrative privileges. Please run PowerShell as Administrator."
        return
    }

    $InterfaceIndex = (Get-NetAdapter | Where-Object { $_.Status -eq "Up" }).InterfaceIndex
    $CurrentDns = (Get-DnsClientServerAddress -InterfaceIndex $InterfaceIndex -AddressFamily IPv4).ServerAddresses

    # Prepare descriptive messages for WhatIf
    $CurrentState = if ($CurrentDns -contains $PiHoleIP) {
        "Current DNS: $PiHoleIP (Pi-hole)"
    } elseif ($CurrentDns) {
        "Current DNS: $($CurrentDns -join ', ') (Current Setting)"
    } else {
        "Current DNS: Automatic (DHCP)"
    }

    $TargetState = if ($CurrentDns -contains $PiHoleIP) {
        "Target DNS:  Automatic (DHCP)"
    } else {
        "Target DNS:  $PiHoleIP (Pi-hole)"
    }

    $WhatIfMsg = @"
$CurrentState
$TargetState
Affects:     All active network adapters
"@

    if ($CurrentDns -contains $PiHoleIP) {
        if ($PSCmdlet.ShouldProcess("DNS Settings", $WhatIfMsg)) {
            Set-DnsClientServerAddress -InterfaceIndex $InterfaceIndex -ResetServerAddresses
        }
    } else {
        if ($PSCmdlet.ShouldProcess("DNS Settings", $WhatIfMsg)) {
            Set-DnsClientServerAddress -InterfaceIndex $InterfaceIndex -ServerAddresses $PiHoleIP
        }
    }

    # Show current state after changes
    $NewDns = Get-DnsClientServerAddress -InterfaceIndex $InterfaceIndex -AddressFamily IPv4
    if (-not $WhatIfPreference) {
        Write-Host "`nCurrent DNS Configuration:" -ForegroundColor Cyan
        $NewDns | Format-Table InterfaceAlias, InterfaceIndex, AddressFamily, ServerAddresses
    }
}
