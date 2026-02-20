# Fix Flutter Android issues. Run in a terminal where "flutter" works.

Write-Host "=== Accepting Android SDK licenses ===" -ForegroundColor Cyan
Write-Host "Run the command below and type 'y' + Enter for each prompt.`n" -ForegroundColor Yellow

flutter doctor --android-licenses

Write-Host "`n=== Checking result ===" -ForegroundColor Cyan
flutter doctor

Write-Host "`nIf Android toolchain still shows [!]: install cmdline-tools via Android Studio:" -ForegroundColor Yellow
Write-Host "  Android Studio -> Settings -> Android SDK -> SDK Tools -> check 'Android SDK Command-line Tools' -> Apply" -ForegroundColor Gray
Write-Host "See scripts/fix_flutter_android.md for full steps.`n" -ForegroundColor Gray
