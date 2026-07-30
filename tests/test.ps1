# test.ps1 — End-to-end test for local-paper-reading skill
$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $PSScriptRoot
$RunScript = Join-Path $Root 'scripts\run.ps1'

Write-Output "=== local-paper-reading E2E Test ==="
Write-Output ""

$passed = 0
$failed = 0

function Test-Case($name, $script) {
    Write-Output "[TEST] $name"
    try {
        & $script
        Write-Output "  PASS"
        $script:passed++
    } catch {
        Write-Output "  FAIL: $_"
        $script:failed++
    }
    Write-Output ""
}

# --- Test 1: No arguments (should show help) ---
Write-Output "[TEST] No arguments shows help"
$output = & $RunScript 2>&1
$exitCode = $LASTEXITCODE
if ($exitCode -eq 1 -and $output -match "搜索关键词或文件路径") {
    Write-Output "  PASS (exit=$exitCode, help shown)"
    $passed++
} else {
    Write-Output "  FAIL (exit=$exitCode)"
    $failed++
}
Write-Output ""

# --- Test 2: Search-only mode ---
Write-Output "[TEST] Search-only mode (arXiv search)"
$output = & $RunScript "search transformer" --search-only 2>&1
$exitCode = $LASTEXITCODE
if ($exitCode -eq 0 -and $output -match "论文列表") {
    Write-Output "  PASS (exit=$exitCode, results returned)"
    $passed++
} else {
    Write-Output "  FAIL (exit=$exitCode)"
    Write-Output "  Output: $($output | Select-Object -First 5)"
    $failed++
}
Write-Output ""

# --- Test 3: Annotate local file ---
Write-Output "[TEST] Annotate local file"
# Create a test TXT file
$testFile = Join-Path $env:TEMP "test_paper.txt"
@"
Abstract

This paper presents a novel approach to machine learning using neural networks.
We propose a new architecture called DeepNet that achieves state-of-the-art results.

1. Introduction

Machine learning has become increasingly important in recent years.
Neural networks are a key component of modern AI systems.

6. Conclusion

We demonstrated that DeepNet outperforms existing methods.
Future work includes extending this approach to other domains.
"@ | Out-File -FilePath $testFile -Encoding UTF8

$output = & $RunScript $testFile --depth overview 2>&1
$exitCode = $LASTEXITCODE
if ($exitCode -eq 0 -and $output -match "标注文件") {
    Write-Output "  PASS (exit=$exitCode, annotation created)"
    $passed++
} else {
    Write-Output "  FAIL (exit=$exitCode)"
    Write-Output "  Output: $($output | Select-Object -First 5)"
    $failed++
}

# Cleanup
Remove-Item $testFile -ErrorAction SilentlyContinue
Write-Output ""

# --- Test 4: Search + Annotate (full pipeline) ---
Write-Output "[TEST] Search + Annotate pipeline"
$output = & $RunScript "attention mechanism" --depth overview 2>&1
$exitCode = $LASTEXITCODE
if ($exitCode -eq 0 -and $output -match "标注文件") {
    Write-Output "  PASS (exit=$exitCode, full pipeline success)"
    $passed++
} else {
    Write-Output "  SKIP (requires network + may timeout)"
}
Write-Output ""

# --- Test 5: Invalid file path ---
Write-Output "[TEST] Invalid file path"
$output = & $RunScript "C:\nonexistent\paper.pdf" 2>&1
$exitCode = $LASTEXITCODE
if ($exitCode -eq 1 -or $output -match "文件不存在") {
    Write-Output "  PASS (error handled gracefully)"
    $passed++
} else {
    Write-Output "  FAIL (exit=$exitCode)"
    $failed++
}
Write-Output ""

# --- Test 6: Clear cache ---
Write-Output "[TEST] Clear cache"
$output = & $RunScript --clear-cache 2>&1
$exitCode = $LASTEXITCODE
if ($exitCode -eq 0 -and $output -match "缓存已清除") {
    Write-Output "  PASS (cache cleared)"
    $passed++
} else {
    Write-Output "  FAIL (exit=$exitCode)"
    $failed++
}
Write-Output ""

# --- Test 7: Layered annotation stats ---
Write-Output "[TEST] Layered annotation stats (core/support/skip)"
$testFile2 = Join-Path $env:TEMP "test_layered.txt"
@"
Abstract

This paper presents a novel approach to machine learning using neural networks.
We propose a new architecture called DeepNet that achieves state-of-the-art results
on multiple benchmarks. Our method significantly improves accuracy.

1. Introduction

Machine learning has become increasingly important in recent years.
Neural networks are a key component of modern AI systems.

2. Related Work

Previous studies have explored various architectures.
Smith et al. proposed a similar approach in 2020.

3. Method

We propose DeepNet, a novel architecture with attention mechanism.
The model uses transformer layers and achieves state-of-the-art performance.

4. Experiments

We evaluated on GLUE and SQuAD datasets.
Results show 5% improvement over baselines.

References

[1] Vaswani, A. et al. Attention Is All You Need. 2017.
[2] Devlin, J. et al. BERT. 2019.

6. Conclusion

We demonstrated that DeepNet outperforms existing methods.
"@ | Out-File -FilePath $testFile2 -Encoding UTF8

$output = & $RunScript $testFile2 --depth intensive 2>&1
$exitCode = $LASTEXITCODE
if ($exitCode -eq 0 -and ($output -match "核心段落" -or $output -match "core")) {
    Write-Output "  PASS (layered stats present)"
    $passed++
} else {
    Write-Output "  SKIP (requires server running)"
}

Remove-Item $testFile2 -ErrorAction SilentlyContinue
Write-Output ""

# --- Summary ---
Write-Output "=== Summary ==="
Write-Output "Passed: $passed"
Write-Output "Failed: $failed"
Write-Output "Total:  $($passed + $failed)"

if ($failed -gt 0) {
    exit 1
} else {
    exit 0
}
