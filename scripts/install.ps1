[CmdletBinding()]
param(
    [string]$InstallDir = "",
    [string]$Python = "",
    [switch]$SkipChecks,
    [switch]$AddToUserPath,
    [switch]$Rollback
)

$ErrorActionPreference = "Stop"

function Resolve-AosRepoRoot {
    return (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

function Resolve-AosPath {
    param([string]$PathValue)

    if ($PathValue.StartsWith("~")) {
        $suffix = $PathValue.Substring(1).TrimStart("\", "/")
        return Join-Path $HOME $suffix
    }
    return [System.Environment]::ExpandEnvironmentVariables($PathValue)
}

function Resolve-AosInstallDir {
    if ($InstallDir) {
        return Resolve-AosPath $InstallDir
    }
    if ($env:AOS_INSTALL_DIR) {
        return Resolve-AosPath $env:AOS_INSTALL_DIR
    }
    if ($env:LOCALAPPDATA) {
        return Join-Path $env:LOCALAPPDATA "AgenticOS\bin"
    }
    return Join-Path $HOME ".aos\bin"
}

function New-AosPythonCommand {
    param(
        [string]$Executable,
        [string[]]$PrefixArgs = @()
    )

    return [pscustomobject]@{
        Executable = $Executable
        PrefixArgs = @($PrefixArgs)
        Display = ((@($Executable) + @($PrefixArgs)) -join " ")
    }
}

function Test-AosPythonCommand {
    param([object]$PythonCommand)

    try {
        & $PythonCommand.Executable @($PythonCommand.PrefixArgs + @("--version")) | Out-Null
        return ($LASTEXITCODE -eq 0)
    }
    catch {
        return $false
    }
}

function Resolve-AosPython {
    $candidates = @()
    if ($Python) {
        $candidates += New-AosPythonCommand -Executable $Python
    }
    if ($env:PYTHON) {
        $candidates += New-AosPythonCommand -Executable $env:PYTHON
    }
    $candidates += New-AosPythonCommand -Executable "py" -PrefixArgs @("-3")
    $candidates += New-AosPythonCommand -Executable "python"

    foreach ($candidate in $candidates) {
        if (Test-AosPythonCommand $candidate) {
            return $candidate
        }
    }

    throw "Could not find a working Python 3 command. Set -Python or the PYTHON environment variable."
}

function Set-AosPythonPath {
    param([string]$RepoRoot)

    $srcPath = Join-Path $RepoRoot "src"
    if ($env:PYTHONPATH) {
        $env:PYTHONPATH = "$srcPath$([System.IO.Path]::PathSeparator)$env:PYTHONPATH"
    }
    else {
        $env:PYTHONPATH = $srcPath
    }
}

function Test-AosWindowsPlatform {
    $windows = [System.Runtime.InteropServices.OSPlatform]::Windows
    return [System.Runtime.InteropServices.RuntimeInformation]::IsOSPlatform($windows)
}

function Get-AosUnitTestArgs {
    if (Test-AosWindowsPlatform) {
        return @(
            "-m",
            "unittest",
            "-v",
            "tests.test_cli_parser",
            "tests.test_distribution_artifacts",
            "tests.test_public_release",
            "tests.test_release_manifest"
        )
    }
    return @("-m", "unittest", "discover", "-s", "tests", "-v")
}

function Escape-PowerShellString {
    param([string]$Value)
    return $Value.Replace("'", "''")
}

function Format-PowerShellArrayLiteral {
    param([string[]]$Values)

    if (-not $Values -or $Values.Count -eq 0) {
        return "@()"
    }
    $quoted = @()
    foreach ($value in $Values) {
        $quoted += "'" + (Escape-PowerShellString $value) + "'"
    }
    return "@(" + ($quoted -join ", ") + ")"
}

function Escape-BatchValue {
    param([string]$Value)

    if ($Value.Contains('"')) {
        throw "Windows launcher values cannot contain double quotes: $Value"
    }
    return $Value.Replace("^", "^^").Replace("%", "%%")
}

function Format-BatchPythonInvocation {
    param([object]$PythonCommand)

    $executable = Escape-BatchValue $PythonCommand.Executable
    $parts = @("`"$executable`"")
    foreach ($arg in $PythonCommand.PrefixArgs) {
        if ($arg.Contains('"')) {
            throw "Windows launcher Python arguments cannot contain double quotes: $arg"
        }
        $parts += $arg
    }
    return ($parts -join " ")
}

function Get-AosStateFile {
    param([string]$TargetDir)
    return Join-Path $TargetDir ".aos-install-state.json"
}

function Get-AosBackupPath {
    param(
        [string]$TargetDir,
        [string]$FileName
    )

    $timestamp = Get-Date -Format "yyyyMMddHHmmss"
    $candidate = Join-Path $TargetDir "$FileName.backup-$timestamp"
    $suffix = 1
    while (Test-Path -LiteralPath $candidate) {
        $candidate = Join-Path $TargetDir "$FileName.backup-$timestamp-$suffix"
        $suffix += 1
    }
    return $candidate
}

function Backup-AosLauncher {
    param(
        [string]$TargetDir,
        [string]$FileName
    )

    $path = Join-Path $TargetDir $FileName
    if (Test-Path -LiteralPath $path -PathType Container) {
        throw "Refusing to replace directory: $path"
    }
    if (Test-Path -LiteralPath $path) {
        $backup = Get-AosBackupPath -TargetDir $TargetDir -FileName $FileName
        Move-Item -LiteralPath $path -Destination $backup
        return $backup
    }
    return $null
}

function Test-AosLauncherTargets {
    param([string]$TargetDir)

    foreach ($fileName in @("aos.cmd", "aos.ps1")) {
        $path = Join-Path $TargetDir $fileName
        if (Test-Path -LiteralPath $path -PathType Container) {
            throw "Refusing to replace directory: $path"
        }
    }
}

function Restore-AosLauncher {
    param(
        [string]$ActivePath,
        [object]$BackupPath
    )

    if ($BackupPath) {
        $backup = [string]$BackupPath
        if (-not (Test-Path -LiteralPath $backup)) {
            throw "Recorded backup is missing: $backup"
        }
    }
    else {
        $backup = $null
    }

    if (Test-Path -LiteralPath $ActivePath -PathType Container) {
        throw "Refusing to remove directory during rollback: $ActivePath"
    }
    if (Test-Path -LiteralPath $ActivePath) {
        Remove-Item -LiteralPath $ActivePath -Force
    }
    if ($backup) {
        Move-Item -LiteralPath $backup -Destination $ActivePath
    }
}

function Write-AosLaunchers {
    param(
        [string]$TargetDir,
        [string]$RepoRoot,
        [object]$PythonCommand
    )

    New-Item -ItemType Directory -Force -Path $TargetDir | Out-Null

    $cmdPath = Join-Path $TargetDir "aos.cmd"
    $repoRootBatch = Escape-BatchValue $RepoRoot
    $pythonInvocation = Format-BatchPythonInvocation $PythonCommand
    $cmdContent = @"
@echo off
setlocal
set "AOS_REPO_ROOT=$repoRootBatch"
set "AOS_COMMAND_PATH=%~f0"
if defined PYTHONPATH (
  set "PYTHONPATH=%AOS_REPO_ROOT%\src;%PYTHONPATH%"
) else (
  set "PYTHONPATH=%AOS_REPO_ROOT%\src"
)
$pythonInvocation -m agentic_os %*
exit /b %ERRORLEVEL%
"@
    Set-Content -Path $cmdPath -Value $cmdContent -Encoding ASCII

    $ps1Path = Join-Path $TargetDir "aos.ps1"
    $repoRootLiteral = Escape-PowerShellString $RepoRoot
    $pythonLiteral = Escape-PowerShellString $PythonCommand.Executable
    $prefixArgsLiteral = Format-PowerShellArrayLiteral $PythonCommand.PrefixArgs
    $ps1Content = @"
`$ErrorActionPreference = "Stop"
`$RepoRoot = '$repoRootLiteral'
`$PythonBin = '$pythonLiteral'
`$PythonPrefixArgs = $prefixArgsLiteral
`$env:AOS_COMMAND_PATH = `$MyInvocation.MyCommand.Path
`$srcPath = Join-Path `$RepoRoot "src"
if (`$env:PYTHONPATH) {
    `$env:PYTHONPATH = "`$srcPath`$([System.IO.Path]::PathSeparator)`$env:PYTHONPATH"
}
else {
    `$env:PYTHONPATH = `$srcPath
}
& `$PythonBin @PythonPrefixArgs -m agentic_os @args
exit `$LASTEXITCODE
"@
    Set-Content -Path $ps1Path -Value $ps1Content -Encoding UTF8
}

function Write-AosInstallState {
    param(
        [string]$TargetDir,
        [string]$RepoRoot,
        [object]$PythonCommand,
        [object]$CmdBackup,
        [object]$Ps1Backup
    )

    $stateFile = Get-AosStateFile $TargetDir
    $payload = [ordered]@{
        installed_at = (Get-Date).ToString("o")
        install_dir = $TargetDir
        active_cmd = (Join-Path $TargetDir "aos.cmd")
        active_ps1 = (Join-Path $TargetDir "aos.ps1")
        backup_cmd = $CmdBackup
        backup_ps1 = $Ps1Backup
        repo_root = $RepoRoot
        python = $PythonCommand.Display
    }
    $payload | ConvertTo-Json | Set-Content -Path $stateFile -Encoding UTF8
}

function Install-AosLaunchers {
    param(
        [string]$TargetDir,
        [string]$RepoRoot,
        [object]$PythonCommand
    )

    New-Item -ItemType Directory -Force -Path $TargetDir | Out-Null
    Test-AosLauncherTargets -TargetDir $TargetDir
    $cmdBackup = $null
    $ps1Backup = $null
    try {
        $cmdBackup = Backup-AosLauncher -TargetDir $TargetDir -FileName "aos.cmd"
        $ps1Backup = Backup-AosLauncher -TargetDir $TargetDir -FileName "aos.ps1"
        Write-AosLaunchers -TargetDir $TargetDir -RepoRoot $RepoRoot -PythonCommand $PythonCommand
        Write-AosInstallState -TargetDir $TargetDir -RepoRoot $RepoRoot -PythonCommand $PythonCommand -CmdBackup $cmdBackup -Ps1Backup $ps1Backup
    }
    catch {
        Restore-AosLauncher -ActivePath (Join-Path $TargetDir "aos.cmd") -BackupPath $cmdBackup
        Restore-AosLauncher -ActivePath (Join-Path $TargetDir "aos.ps1") -BackupPath $ps1Backup
        throw
    }
}

function Rollback-AosInstall {
    param([string]$TargetDir)

    $stateFile = Get-AosStateFile $TargetDir
    if (-not (Test-Path -LiteralPath $stateFile)) {
        throw "Install state file is missing: $stateFile"
    }
    $state = Get-Content -LiteralPath $stateFile -Raw | ConvertFrom-Json
    Restore-AosLauncher -ActivePath $state.active_cmd -BackupPath $state.backup_cmd
    Restore-AosLauncher -ActivePath $state.active_ps1 -BackupPath $state.backup_ps1
    Remove-Item -LiteralPath $stateFile -Force
    Write-Host "aos Windows rollback complete: $TargetDir"
}

function Invoke-AosPython {
    param(
        [object]$PythonCommand,
        [string[]]$Arguments
    )

    & $PythonCommand.Executable @($PythonCommand.PrefixArgs + $Arguments)
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed: $($PythonCommand.Display) $($Arguments -join ' ')"
    }
}

function Invoke-AosCommand {
    param(
        [string]$FilePath,
        [string[]]$Arguments
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed: $FilePath $($Arguments -join ' ')"
    }
}

function Test-PathContainsInstallDir {
    param([string]$TargetDir)

    $allPathValues = @(
        $env:PATH,
        [Environment]::GetEnvironmentVariable("Path", "User")
    ) -join ";"
    $parts = $allPathValues -split ";" | Where-Object { $_ }
    return $parts -contains $TargetDir
}

function Add-InstallDirToUserPath {
    param([string]$TargetDir)

    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $parts = @()
    if ($userPath) {
        $parts = $userPath -split ";" | Where-Object { $_ }
    }
    if ($parts -notcontains $TargetDir) {
        $newPath = (@($parts) + $TargetDir) -join ";"
        [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
    }
}

$repoRoot = Resolve-AosRepoRoot
$installPath = Resolve-AosInstallDir

if ($Rollback) {
    Rollback-AosInstall -TargetDir $installPath
    return
}

$pythonCommand = Resolve-AosPython
$skipChecksFlag = $SkipChecks -or ($env:AOS_INSTALL_SKIP_CHECKS -eq "1")
$originalPythonPath = $env:PYTHONPATH

Write-Host "AOS Windows install checks:"
Write-Host "  No private data is uploaded. The installer writes launchers and uses temporary checks."
Write-Host "  Python: $($pythonCommand.Display)"

try {
    Set-AosPythonPath $repoRoot

    if (-not $skipChecksFlag) {
        Write-Host "  1/5 unit tests"
        if (Test-AosWindowsPlatform) {
            Write-Host "      using Windows-compatible unittest gate"
        }
        Invoke-AosPython -PythonCommand $pythonCommand -Arguments (Get-AosUnitTestArgs)

        Write-Host "  2/5 readiness smoke"
        $tempLauncherDir = Join-Path ([System.IO.Path]::GetTempPath()) ("aos-install-launcher-" + [guid]::NewGuid().ToString("N"))
        try {
            Write-AosLaunchers -TargetDir $tempLauncherDir -RepoRoot $repoRoot -PythonCommand $pythonCommand
            $readinessScript = Join-Path $repoRoot "scripts\readiness_smoke.py"
            $tempLauncher = Join-Path $tempLauncherDir "aos.cmd"
            Invoke-AosPython $pythonCommand @($readinessScript, "--launcher", $tempLauncher, "--json")
        }
        finally {
            if (Test-Path -LiteralPath $tempLauncherDir) {
                Remove-Item -Recurse -Force -LiteralPath $tempLauncherDir
            }
        }
    }
    else {
        Write-Host "  1/5 unit tests skipped by AOS_INSTALL_SKIP_CHECKS=1"
        Write-Host "  2/5 readiness smoke skipped by AOS_INSTALL_SKIP_CHECKS=1"
    }

    Write-Host "  3/5 install launchers"
    Install-AosLaunchers -TargetDir $installPath -RepoRoot $repoRoot -PythonCommand $pythonCommand

    $aosCmd = Join-Path $installPath "aos.cmd"
    if (-not $skipChecksFlag) {
        $cleanCheckHome = $false
        if ($env:AOS_INSTALL_CHECK_HOME) {
            $checkHome = Resolve-AosPath $env:AOS_INSTALL_CHECK_HOME
        }
        else {
            $checkHome = Join-Path ([System.IO.Path]::GetTempPath()) ("aos-install-check-" + [guid]::NewGuid().ToString("N"))
            $cleanCheckHome = $true
        }

        try {
            Write-Host "  4/5 temporary doctor"
            Invoke-AosCommand $aosCmd @("--os-home", $checkHome, "init")
            Invoke-AosCommand $aosCmd @("--os-home", $checkHome, "doctor", "--summary")
        }
        finally {
            if ($cleanCheckHome -and (Test-Path -LiteralPath $checkHome)) {
                Remove-Item -Recurse -Force -LiteralPath $checkHome
            }
        }
    }
    else {
        Write-Host "  4/5 temporary doctor skipped by AOS_INSTALL_SKIP_CHECKS=1"
    }

    Write-Host "  5/5 version"
    Invoke-AosCommand $aosCmd @("version")

    if ($AddToUserPath) {
        Add-InstallDirToUserPath $installPath
        Write-Host "Added $installPath to the User PATH. Open a new PowerShell window before running aos."
    }
    elseif (-not (Test-PathContainsInstallDir $installPath)) {
        Write-Host "Note: $installPath is not on PATH. Re-run with -AddToUserPath or add it manually."
    }

    Write-Host "aos Windows install complete: $aosCmd"
    Write-Host "Next: run 'aos init' if this is your first Agentic OS install."
    Write-Host "Rollback: powershell -ExecutionPolicy Bypass -File scripts\install.ps1 -Rollback"
}
finally {
    $env:PYTHONPATH = $originalPythonPath
}
