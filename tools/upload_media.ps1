<#
    Push the media originals to Cloudflare R2.

        .\tools\upload_media.ps1 -Setup     # once, to configure the rclone remote
        .\tools\upload_media.ps1            # upload
        .\tools\upload_media.ps1 -List      # just print what would go
        .\tools\upload_media.ps1 -WhatIf    # dry run, uploads nothing

    media.html links to these; it does not host them. They are too big for
    GitHub Pages, which rejects any file over 100 MB and caps a whole site at 1 GB.

    Every file is named explicitly below rather than matched by a filter.
    rclone's --include / --exclude precedence is easy to get subtly wrong — an
    --exclude placed alongside an --include was silently losing here — and with a
    handful of files an explicit list is both safer and self-documenting: what you
    read below is exactly what lands in the bucket.

    Nothing secret is stored in this repo. -Setup hands your keys straight to
    rclone, which keeps them in %APPDATA%\rclone\rclone.conf.
#>
[CmdletBinding()]
param(
    [string]$Source = "C:\Users\p\Downloads\PeterStreetBasin2026sep06-1-001",
    [string]$Remote = "lovequay-r2",
    [string]$Bucket = "lovequay-media",
    [switch]$Setup,
    [switch]$WhatIf,
    [switch]$List
)

$ErrorActionPreference = "Stop"

# Attach = $true sends Content-Disposition: attachment, so a click saves the file
# rather than trying to render it. The HTML download attribute is ignored on
# cross-origin links, and without this a click on the 3840 GIF would ask the
# browser to paint 780 MB of animation in a tab.
$Files = @(
    @{ Name = "LoveQuay-splat-transparent-640.gif";   Attach = $false }
    @{ Name = "LoveQuay-splat-transparent-1920.webm"; Attach = $false }
    @{ Name = "LoveQuay-splat-transparent-1280.webp"; Attach = $false }
    @{ Name = "LoveQuay-splat-transparent-1920.gif";  Attach = $true  }
    @{ Name = "LoveQuay-splat-transparent-3840.gif";  Attach = $true  }
    @{ Name = "LoveQuay_2026-09-17_rc0011b_merge001_20MCompColor_dbros.mp4"; Attach = $true }
)

function Get-Rclone {
    $cmd = Get-Command rclone -ErrorAction SilentlyContinue
    if ($null -eq $cmd) {
        Write-Host "rclone is not installed. Install it with:" -ForegroundColor Red
        Write-Host "    winget install Rclone.Rclone"
        exit 1
    }
    return $cmd.Source
}

function Test-Remote {
    $remotes = rclone listremotes 2>$null
    return ($remotes -contains "${Remote}:")
}

function Show-Plan {
    Write-Host ""
    Write-Host ("{0,-60} {1,10}  {2}" -f "FILE", "SIZE", "SERVED AS")
    Write-Host (("-" * 60) + " " + ("-" * 10) + "  " + ("-" * 9))
    $total = 0
    foreach ($f in $Files) {
        $path = Join-Path $Source $f.Name
        if (-not (Test-Path $path)) {
            Write-Host ("{0,-60} {1,10}  MISSING" -f $f.Name, "-") -ForegroundColor Red
            continue
        }
        $len = (Get-Item $path).Length
        $total += $len
        $how = "inline"
        if ($f.Attach) { $how = "download" }
        Write-Host ("{0,-60} {1,10}  {2}" -f $f.Name, ("{0:N1} MB" -f ($len / 1MB)), $how)
    }
    Write-Host (("-" * 60) + " " + ("-" * 10))
    Write-Host ("{0,-60} {1,10}" -f "$($Files.Count) files", ("{0:N2} GB" -f ($total / 1GB)))
    Write-Host ""
}

function Invoke-Setup {
    Write-Host ""
    Write-Host "Cloudflare R2 setup" -ForegroundColor Cyan
    Write-Host "-------------------"
    Write-Host "In the Cloudflare dashboard first:"
    Write-Host "  1. R2 -> Create bucket, named '$Bucket'."
    Write-Host "  2. That bucket -> Settings -> Public access -> Connect a custom domain,"
    Write-Host "     and enter 'media.lovequay.com'. Cloudflare adds the DNS record."
    Write-Host "     Do not use the r2.dev URL in production; it is rate limited."
    Write-Host "  3. R2 -> Manage API tokens -> Create token, Object Read and Write."
    Write-Host ""
    Write-Host "Then paste the three values. They go straight into rclone's own config"
    Write-Host "and are never written into this repository."
    Write-Host ""

    $account = Read-Host "Cloudflare Account ID"
    $keyId   = Read-Host "R2 Access Key ID"
    $secure  = Read-Host "R2 Secret Access Key" -AsSecureString
    $bstr    = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    $secret  = [Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)

    rclone config create $Remote s3 `
        provider=Cloudflare `
        access_key_id=$keyId `
        secret_access_key=$secret `
        endpoint="https://$account.r2.cloudflarestorage.com" `
        acl=private | Out-Null

    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    $secret = $null

    if (Test-Remote) {
        Write-Host ""
        Write-Host "Remote '$Remote' configured. Run it again without -Setup to upload." -ForegroundColor Green
    } else {
        Write-Host "Something went wrong - '$Remote' still is not listed." -ForegroundColor Red
        exit 1
    }
}

# --- go ---------------------------------------------------------------------

Get-Rclone | Out-Null

if (-not (Test-Path $Source)) {
    Write-Host "Source folder not found: $Source" -ForegroundColor Red
    exit 1
}

if ($Setup) { Invoke-Setup; exit 0 }
if ($List)  { Show-Plan;    exit 0 }

if (-not (Test-Remote)) {
    Write-Host "rclone remote '$Remote' is not configured yet." -ForegroundColor Yellow
    Write-Host "Run this first:  .\tools\upload_media.ps1 -Setup"
    exit 1
}

Show-Plan
if ($WhatIf) { Write-Host "Dry run - nothing will be written." -ForegroundColor Yellow }

foreach ($f in $Files) {
    $path = Join-Path $Source $f.Name
    if (-not (Test-Path $path)) {
        Write-Host "skipping (not found): $($f.Name)" -ForegroundColor Yellow
        continue
    }

    $a = @("copyto", $path, "${Remote}:${Bucket}/$($f.Name)",
           "--s3-upload-cutoff", "100M", "--s3-chunk-size", "64M",
           "--progress", "--stats-one-line")
    if ($f.Attach) {
        $a += @("--header-upload", ('Content-Disposition: attachment; filename="' + $f.Name + '"'))
        # rclone skips a file whose size and modtime already match the
        # destination, which on a re-run would leave the header unapplied.
        $a += "--ignore-times"
    }
    if ($WhatIf) { $a += "--dry-run" }

    Write-Host ""
    Write-Host "-> $($f.Name)" -ForegroundColor Cyan
    & rclone @a
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed on $($f.Name) (rclone exit $LASTEXITCODE)." -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

Write-Host ""
Write-Host "Done. Spot-check both kinds:" -ForegroundColor Green
Write-Host "    curl.exe -sI https://media.lovequay.com/LoveQuay-splat-transparent-640.gif"
Write-Host "    curl.exe -sI https://media.lovequay.com/LoveQuay-splat-transparent-3840.gif"
Write-Host "  (only the second should carry Content-Disposition: attachment)"
