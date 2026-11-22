# agent.ps1 - run by scheduled task EboAgent in the console session: executes C:\agentwork\ebo\cmd.ps1 with lib.ps1
# loaded, output to out.txt, then writes done.txt.
$d = 'C:\agentwork\ebo'; Remove-Item "$d\done.txt" -ErrorAction SilentlyContinue
try { . "$d\lib.ps1"; if (Test-Path "$d\ebo.ps1") { . "$d\ebo.ps1" }; & "$d\cmd.ps1" *>&1 | % { ($_ | Out-String -Width 400).TrimEnd() | Add-Content "$d\out.txt" -Encoding UTF8 } }
catch { "EXC: $($_.Exception.Message)`n$($_.ScriptStackTrace)" | Add-Content "$d\out.txt" }
'done' | Set-Content "$d\done.txt"
