<#
Print the target, arguments and working folder of every MapleStory desktop
shortcut, so you can find what the launch task should run.

Looks at .lnk files on your own desktop and the Public desktop whose names
contain "maple". The Target is the Nexon launcher exe and the Arguments are
its "launch this game" link (e.g. nxl://launch/10100) - together, what the
MesoMarketCollector_MapleStoryViaLauncher task runs. Use it when the README's
setup prints nothing for $sc.TargetPath, or the shortcut isn't named
MapleStory.lnk.

Usage, from the repo root: .\tools\find_shortcut_target.ps1
#>
$shell = New-Object -ComObject WScript.Shell
$paths = @(
    "$env:USERPROFILE\Desktop\*.lnk",
    "$env:PUBLIC\Desktop\*.lnk"
)
Get-ChildItem -Path $paths -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -like '*maple*' } |
    ForEach-Object {
        $sc = $shell.CreateShortcut($_.FullName)
        [PSCustomObject]@{
            Shortcut  = $_.FullName
            Target    = $sc.TargetPath
            Arguments = $sc.Arguments
            WorkDir   = $sc.WorkingDirectory
        }
    } | Format-List
