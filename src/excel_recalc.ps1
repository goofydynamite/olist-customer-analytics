# Windows + Excel step, run after src/build_excel.py:
#   1. adds the Raw_Data and Cleaned_Data tabs (full orders table before / after cleaning),
#      imported natively by Excel because ~100k rows is too heavy for openpyxl
#   2. recalculates every formula (so cached values exist for previewers / GitHub)
#   3. optionally renders the Dashboard sheet to a PNG
#
#   powershell -File src/excel_recalc.ps1 [-Png reports/figures/10_excel_dashboard.png]
param([string]$Png = "")
$root = Split-Path -Parent $PSScriptRoot
$p = Join-Path $root "excel\Olist_Customer_Dashboard.xlsx"

# Excel column types for the text import: 1 = General, 2 = Text, 5 = date (YMD)
$tabs = @(
    @{ Name  = "Raw_Data"
       Csv   = "data\raw\olist_orders_dataset.csv"
       Title = "Raw data: olist_orders_dataset.csv exactly as downloaded (99,441 orders)"
       Note  = "Highlighted: red = 'delivered' but no delivery date; grey = canceled / unavailable. The other 8 raw files are in data/raw/ in the repo."
       Types = [int[]](2, 2, 2, 5, 5, 5, 5, 5) },
    @{ Name  = "Cleaned_Data"
       Csv   = "data\cleaned\orders.csv"
       Title = "Cleaned data: the same orders after src/etl.py (typed dates + delivery metrics)"
       Note  = "Added columns: is_delivered, delivery_days, estimated_days, days_late (+ = late), is_late, purchase_month. Highlighted: late deliveries. All 8 cleaned tables are in data/cleaned/."
       Types = [int[]](2, 2, 2, 5, 5, 5, 5, 5, 1, 1, 1, 1, 1, 2) }
)

$x = New-Object -ComObject Excel.Application
$x.Visible = $false; $x.DisplayAlerts = $false; $x.ScreenUpdating = $false
$wb = $x.Workbooks.Open($p)

foreach ($t in $tabs) {
    foreach ($s in @($wb.Worksheets)) { if ($s.Name -eq $t.Name) { $s.Delete() } }
    $ws = $wb.Worksheets.Add([Type]::Missing, $wb.Worksheets.Item($wb.Worksheets.Count))
    $ws.Name = $t.Name
    $x.ActiveWindow.DisplayGridlines = $false

    $csv = Join-Path $root $t.Csv
    $qt = $ws.QueryTables.Add("TEXT;$csv", $ws.Range("A4"))
    $qt.TextFilePlatform = 65001          # UTF-8
    $qt.TextFileParseType = 1             # delimited
    $qt.TextFileCommaDelimiter = $true
    $qt.TextFileTextQualifier = 1         # double quote
    $qt.TextFileColumnDataTypes = $t.Types
    $qt.AdjustColumnWidth = $true
    $qt.Refresh($false) | Out-Null
    $qt.Delete()                          # keep the data, drop the live link to the CSV
    foreach ($c in @($wb.Connections)) { $c.Delete() }

    $used = $ws.Range("A4").CurrentRegion
    $lo = $ws.ListObjects.Add(1, $used, [Type]::Missing, 1)
    $lo.Name = "t" + ($t.Name -replace "_", "")
    $lo.TableStyle = "TableStyleLight9"
    $rows = $used.Rows.Count
    $cols = $used.Columns.Count
    $last = $ws.Cells.Item(4 + $rows - 1, $cols).Address($false, $false)
    $body = $ws.Range("A5:$last")

    foreach ($c in 1..$cols) {
        $hdr = $ws.Cells.Item(4, $c).Text
        if ($hdr -like "*timestamp*" -or $hdr -like "*_at" -or $hdr -like "*_date") {
            $ws.Columns.Item($c).NumberFormat = "yyyy-mm-dd hh:mm:ss"
        }
    }

    if ($t.Name -eq "Raw_Data") {
        $fc = $body.FormatConditions.Add(2, [Type]::Missing, '=AND($C5="delivered",$G5="")')
        $fc.Interior.Color = 0xC7CEFE        # light red (BGR)
        $fc = $body.FormatConditions.Add(2, [Type]::Missing, '=OR($C5="canceled",$C5="unavailable")')
        $fc.Interior.Color = 0xE5E7EB        # light grey
    } else {
        $fc = $body.FormatConditions.Add(2, [Type]::Missing, '=$M5=1')
        $fc.Interior.Color = 0xC7CEFE
        foreach ($c in 10..12) { $ws.Columns.Item($c).NumberFormat = "0.00" }
    }

    $ws.Range("A1").Value2 = $t.Title
    $ws.Range("A1").Font.Size = 16; $ws.Range("A1").Font.Bold = $true
    $ws.Range("A2").Value2 = $t.Note
    $ws.Range("A2").Font.Italic = $true; $ws.Range("A2").Font.Color = 0x80726B
    $ws.Range("A1:A2").Font.Name = "Arial"
    $ws.Columns.Item(1).ColumnWidth = 36; $ws.Columns.Item(2).ColumnWidth = 36
    $ws.Activate(); $ws.Range("B5").Select() | Out-Null
    $x.ActiveWindow.FreezePanes = $true
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
