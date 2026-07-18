. {
    Get-ChildItem 'HKCU:\Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\microphone\NonPackaged' | ForEach-Object {
        $path = $_.Name -replace 'HKEY_CURRENT_USER', 'HKCU:'
        $val = (Get-ItemProperty -Path $path).Value
        [PSCustomObject]@{
            Name = $_.Name
            Value = $val
        }
    }
} | Format-List
