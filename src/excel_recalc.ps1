# Recalculate the workbook in Excel (so cached values exist for previewers/GitHub)
# and optionally render the Dashboard sheet to a PNG.
#   powershell -File src/excel_recalc.ps1 [-Png reports/figures/excel_dashboard.png]
param([string]$Png = "")
$root = Split-Path -Parent $PSScriptRoot
$p = Join-Path $root "excel\Olist_Customer_Dashboard.xlsx"
$x = New-Object -ComObject Excel.Application
$x.Visible = $false; $x.DisplayAlerts = $false
$wb = $x.Workbooks.Open($p)
$x.CalculateFull()
$wb.Worksheets.Item("Dashboard").Activate()
$wb.Save()
if ($Png) {
    $out = if ([System.IO.Path]::IsPathRooted($Png)) { $Png } else { Join-Path $root $Png }
    $ws = $wb.Worksheets.Item("Dashboard")
    $rng = $ws.Range("A1:Z66")
    $rng.CopyPicture(1, 2) | Out-Null
    $co = $ws.ChartObjects().Add(0, 0, $rng.Width, $rng.Height)
    $co.Activate() | Out-Null; $co.Chart.Paste() | Out-Null
    $co.Chart.Export($out) | Out-Null
    $co.Delete()
}
$wb.Close($false); $x.Quit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($x) | Out-Null
Write-Output "recalculated $p"
