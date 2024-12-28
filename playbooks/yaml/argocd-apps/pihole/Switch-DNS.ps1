<#
.SYNOPSIS
Switches the DNS configuration between a Pi-hole DNS server and the default DNS.

.DESCRIPTION
The `Switch-DNS` function toggles the DNS server settings for the active network adapter.
If the current DNS server is set to the Pi-hole IP, it resets to the default (automatic DNS).
If not, it switches to the specified Pi-hole IP.

.PARAMETER PiHoleIP
The IP address of the Pi-hole DNS server. Defaults to "192.168.1.122".

.EXAMPLE
Switch-DNS
Switches the DNS to the Pi-hole server (192.168.1.122) or back to the default.

.EXAMPLE
Switch-DNS -PiHoleIP "192.168.1.200"
Switches the DNS to a custom Pi-hole server (192.168.1.200) or back to the default.

.EXAMPLE
Switch-DNS -WhatIf
Previews the DNS changes without applying them.

.NOTES
This script modifies the DNS configuration for the active network adapter and requires
elevated permissions to run.
#>

function Switch-DNS {
    [CmdletBinding(SupportsShouldProcess)]
    param (
        [string]$PiHoleIP = "192.168.1.122"
    )

    # Check for admin privileges
    if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
        Write-Error "This script requires administrative privileges. Please run PowerShell as Administrator."
        return
    }

    $InterfaceIndex = (Get-NetAdapter | Where-Object { $_.Status -eq "Up" }).InterfaceIndex
    $CurrentDns = (Get-DnsClientServerAddress -InterfaceIndex $InterfaceIndex -AddressFamily IPv4).ServerAddresses

    if ($CurrentDns -contains $PiHoleIP) {
        if ($PSCmdlet.ShouldProcess("DNS Settings", "Resetting DNS to default (automatic DNS)")) {
            Set-DnsClientServerAddress -InterfaceIndex $InterfaceIndex -ResetServerAddresses
        }
    } else {
        if ($PSCmdlet.ShouldProcess("DNS Settings", "Setting DNS to Pi-hole IP: $PiHoleIP")) {
            Set-DnsClientServerAddress -InterfaceIndex $InterfaceIndex -ServerAddresses $PiHoleIP
        }
    }

    Get-DnsClientServerAddress -InterfaceIndex $InterfaceIndex -AddressFamily IPv4
}
