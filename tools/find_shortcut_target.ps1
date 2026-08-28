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
