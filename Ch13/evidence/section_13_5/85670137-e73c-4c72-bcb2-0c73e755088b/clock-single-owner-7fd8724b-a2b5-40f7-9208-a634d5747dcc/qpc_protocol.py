"""Read-only host QPC handshake: READY follows serializer initialization."""


def server_expression(*,warm=True):
    # The first ConvertTo-Json can take nearly a second. READY must mean this
    # SAME response path is initialized, before the fixed measurement window.
    # Neither timestamps nor interval bounds are changed or selected by RTT.
    sample='(@{qpc=[Diagnostics.Stopwatch]::GetTimestamp();frequency=[Diagnostics.Stopwatch]::Frequency;utc=[DateTimeOffset]::UtcNow.ToString("o")} | ConvertTo-Json -Compress)'
    return ('function Get-OriginalClockSample { '+sample+' }; '
        + ('$null=Get-OriginalClockSample; ' if warm else '')
        + '[Console]::WriteLine("READY"); '
        + 'while(($line=[Console]::ReadLine()) -ne $null) { '
        + 'if($line -eq "stop") { break }; '
        + '[Console]::WriteLine((Get-OriginalClockSample)) }')
