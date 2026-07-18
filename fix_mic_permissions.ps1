$pythonPath = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\microphone\NonPackaged\C:#Users#UserBempe#AppData#Local#Python#pythoncore-3.14-64#python.exe'
if (-not (Test-Path $pythonPath)) {
    New-Item -Path $pythonPath -Force | Out-Null
}
Set-ItemProperty -Path $pythonPath -Name 'Value' -Value 'Allow'
$value = (Get-ItemProperty -Path $pythonPath -Name 'Value').Value
Write-Host "Python microphone permission set to: $value"
