# Windows + Excel step, run after src/build_excel.py:
#   1. adds the Orders_Raw and Orders_Clean tabs (orders table before / after cleaning);
#      Excel imports them itself because ~100k rows is too heavy for openpyxl
#   2. recalculates every formula
#   3. optionally renders the Dashboard sheet to a PNG
#
#   powershell -File src/excel_recalc.ps1 [-Png reports/figures/10_excel_dashboard.png]
param([string]$Png = "")
$root = Split-Path -Parent $PSScriptRoot
$p = Join-Path $root "excel\Olist_Customer_Dashboard.xlsx"

# column types for the import: 1 = General, 2 = Text, 5 = date (YMD)
$tabs = @(
    @{ Name = "Orders_Raw";   Csv = "data\raw\olist_orders_dataset.csv"; Types = [int[]](2, 2, 2, 5, 5, 5, 5, 5) },
    @{ Name = "Orders_Clean"; Csv = "data\cleaned\orders.csv";            Types = [int[]](2, 2, 2, 5, 5, 5, 5, 5, 1, 1, 1, 1, 1, 2) }
)

$x = New-Object -ComObject Excel.Application
$x.Visible = $false; $x.DisplayAlerts = $false; $x.ScreenUpdating = $false
$wb = $x.Workbooks.Open($p)

foreach ($t in $tabs) {
    foreach ($s in @($wb.Worksheets)) { if ($s.Name -eq $t.Name) { $s.Delete() } }
    $ws = $wb.Worksheets.Add([Type]::Missing, $wb.Worksheets.Item($wb.Worksheets.Count))
    $ws.Name = $t.Name

    $qt = $ws.QueryTables.Add("TEXT;" + (Join-Path $root $t.Csv), $ws.Range("A1"))
    $qt.TextFilePlatform = 65001
    $qt.TextFileParseType = 1
    $qt.TextFileCommaDelimiter = $true
    $qt.TextFileTextQualifier = 1
    $qt.TextFileColumnDataTypes = $t.Types
    $qt.Refresh($false) | Out-Null
    $qt.Delete()
    foreach ($c in @($wb.Connections)) { $c.Delete() }

    $lo = $ws.ListObjects.Add(1, $ws.Range("A1").CurrentRegion, [Type]::Missing, 1)
    $lo.Name = $t.Name
    $lo.TableStyle = "TableStyleMedium2"

    $cols = $lo.ListColumns.Count
    foreach ($c in 1..$cols) {
        $h = $ws.Cells.Item(1, $c).Text
        if ($h -like "*timestamp*" -or $h -like "*_at" -or $h -like "*_date") {
            $ws.Columns.Item($c).NumberFormat = "yyyy-mm-dd hh:mm:ss"
        }
        if ($h -in @("delivery_days", "estimated_days")) { $ws.Columns.Item($c).NumberFormat = "0.00" }
    }
    $ws.Range("A1").CurrentRegion.Font.Name = "Calibri"
    $ws.Range("A1").CurrentRegion.Font.Size = 11
    $ws.Columns.AutoFit() | Out-Null

    $ws.Activate()
    $x.ActiveWindow.ScrollRow = 1; $x.ActiveWindow.ScrollColumn = 1
    $ws.Range("A2").Select() | Out-Null
    $x.ActiveWindow.FreezePanes = $true
    $ws.Range("A1").Select() | Out-Null
}

$x.CalculateFull()
$wb.Worksheets.Item("Dashboard").Activate()
$x.ScreenUpdating = $true
$wb.Save()
if ($Png) {
    $out = if ([System.IO.Path]::IsPathRooted($Png)) { $Png } else { Join-Path $root $Png }
    $ws = $wb.Worksheets.Item("Dashboard")
    $rng = $ws.Range("A1:Z67")
    $rng.CopyPicture(1, 2) | Out-Null
    $co = $ws.ChartObjects().Add(0, 0, $rng.Width, $rng.Height)
    $co.Activate() | Out-Null; $co.Chart.Paste() | Out-Null
    $co.Chart.Export($out) | Out-Null
    $co.Delete()
    $wb.Save()
}
$wb.Close($false); $x.Quit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($x) | Out-Null
Write-Output "added data tabs, recalculated $p"
