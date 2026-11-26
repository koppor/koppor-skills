# Render every slide of a .pptx to PNG with PowerPoint, to compare a drawn diagram with the
# notation reference. Usage: pwsh render.ps1 <deck.pptx> [<output folder>] [<width in px>]
# A PowerPoint that is already running is reused and left open.
param(
    [Parameter(Mandatory = $true)][string]$Deck,
    [string]$Out = "",
    [int]$Width = 2880
)
$ErrorActionPreference = "Stop"
$deckPath = (Resolve-Path -LiteralPath $Deck).Path
if (-not $Out) { $Out = Join-Path (Split-Path $deckPath) ((Split-Path $deckPath -LeafBase) + "-png") }
New-Item -ItemType Directory -Force $Out | Out-Null
$outPath = (Resolve-Path -LiteralPath $Out).Path

$wasRunning = [bool](Get-Process POWERPNT -ErrorAction SilentlyContinue)
$app = New-Object -ComObject PowerPoint.Application
try {
    # ReadOnly, not Untitled, no window
    $pres = $app.Presentations.Open($deckPath, $true, $false, $false)
    $height = [int]($Width * $pres.PageSetup.SlideHeight / $pres.PageSetup.SlideWidth)
    foreach ($slide in $pres.Slides) {
        $png = Join-Path $outPath ("slide-{0:d2}.png" -f $slide.SlideIndex)
        $slide.Export($png, "PNG", $Width, $height)
        Write-Output $png
    }
    $pres.Close()
}
finally {
    if (-not $wasRunning) { $app.Quit() }
    [void][Runtime.InteropServices.Marshal]::ReleaseComObject($app)
}
