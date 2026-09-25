@echo off
setlocal
pushd "%~dp0"

echo Building Comedy Gold Miner.exe...
if exist ".build" rmdir /s /q ".build"
if exist "src\MinerHost\bin" rmdir /s /q "src\MinerHost\bin"
if exist "src\MinerHost\obj" rmdir /s /q "src\MinerHost\obj"
dotnet publish "src\MinerHost\MinerHost.csproj" -c Release -r win-x64 --self-contained false -o ".build"
if errorlevel 1 goto :failed
if not exist ".build\Miner.exe" goto :failed
copy /y ".build\Miner.exe" "Miner.exe" >nul
if errorlevel 1 goto :failed
rmdir /s /q ".build"
if exist "src\MinerHost\bin" rmdir /s /q "src\MinerHost\bin"
if exist "src\MinerHost\obj" rmdir /s /q "src\MinerHost\obj"
echo VERIFIED: Miner.exe
popd
exit /b 0

:failed
echo Miner build failed.
if exist ".build" rmdir /s /q ".build"
if exist "src\MinerHost\bin" rmdir /s /q "src\MinerHost\bin"
if exist "src\MinerHost\obj" rmdir /s /q "src\MinerHost\obj"
popd
exit /b 1
