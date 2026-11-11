<#
.SYNOPSIS
    Dong goi do an Introduction to AI theo dung format quy dinh cua de bai:
    AI_final_<Project Group ID>_<Student ID>/
      ├── source/
      │     ├── task1/
      │     ├── task2/
      │     ├── task3/
      │     ├── README.md
      │     └── requirements.txt
      ├── report.pdf
      └── demo.txt

.EXAMPLE
    .\package_submission.ps1 -GroupId "G01" -StudentId "523H0178"
#>

param(
    [Parameter(Mandatory=$true, HelpMessage="Nhap ma nhom (vi du: G01, Nhom05)")]
    [string]$GroupId,

    [Parameter(Mandatory=$true, HelpMessage="Nhap MSSV (vi du: 523H0178)")]
    [string]$StudentId
)

$baseName = "AI_final_${GroupId}_${StudentId}"
$outDir = Join-Path -Path $PSScriptRoot -ChildPath $baseName
$zipFile = Join-Path -Path $PSScriptRoot -ChildPath "$baseName.zip"

Write-Host "Dang tao goi nop bai: $baseName ..." -ForegroundColor Cyan

# Xoa thu muc cu neu co
if (Test-Path $outDir) { Remove-Item -Recurse -Force $outDir }
if (Test-Path $zipFile) { Remove-Item -Force $zipFile }

# 1. Tao thu muc goc va source/
$sourceDir = Join-Path $outDir "source"
New-Item -ItemType Directory -Path $sourceDir -Force | Out-Null

# 2. Chep task1, task2, task3 (bo qua .venv, __pycache__, .git)
foreach ($t in @("task1", "task2", "task3")) {
    $srcPath = Join-Path $PSScriptRoot $t
    $dstPath = Join-Path $sourceDir $t
    robocopy $srcPath $dstPath /E /XD .venv .venv-windows-old __pycache__ /XF *.pyc .DS_Store /NFL /NDL /NJH /NJS | Out-Null
}

# 3. Chep README.md va requirement.txt vao source/
Copy-Item (Join-Path $PSScriptRoot "README.md") (Join-Path $sourceDir "README.md")
# Tao file REAME.md de dap ung chinh xac yeu cau typo trong de bai PDF ("REAME.md and requirement.txt")
Copy-Item (Join-Path $PSScriptRoot "README.md") (Join-Path $sourceDir "REAME.md")

# Gop requirement.txt cho source/
$reqMerged = @(
    "python-sat>=0.1.8.dev1",
    "pygame>=2.5.0",
    "matplotlib>=3.5.0"
)
$reqMerged | Set-Content (Join-Path $sourceDir "requirement.txt")
$reqMerged | Set-Content (Join-Path $sourceDir "requirements.txt")

# 4. Chep report.pdf va demo.txt vao goc thu muc nop
if (Test-Path (Join-Path $PSScriptRoot "report.pdf")) {
    Copy-Item (Join-Path $PSScriptRoot "report.pdf") (Join-Path $outDir "report.pdf")
} else {
    Write-Warning "Khong tim thay report.pdf o thu muc goc!"
}

if (Test-Path (Join-Path $PSScriptRoot "demo.txt")) {
    Copy-Item (Join-Path $PSScriptRoot "demo.txt") (Join-Path $outDir "demo.txt")
} else {
    Set-Content (Join-Path $outDir "demo.txt") "https://"
}

# 5. Nen thanh file ZIP
Write-Host "Dang nen file ZIP: $zipFile ..." -ForegroundColor Cyan
Compress-Archive -Path $outDir -DestinationPath $zipFile -Force

# 6. Don dep thu muc tam
Remove-Item -Recurse -Force $outDir

Write-Host "==========================================" -ForegroundColor Green
Write-Host "Da dong goi thanh cong:" -ForegroundColor Green
Write-Host "File nop bai: $zipFile" -ForegroundColor Yellow
Write-Host "Kiem tra lai link trong demo.txt truoc khi nop nhe!" -ForegroundColor Yellow
Write-Host "==========================================" -ForegroundColor Green

