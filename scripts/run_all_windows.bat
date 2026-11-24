@echo off
setlocal
cd /d %~dp0\..

echo === 1. Generate tests ===
py tests\gen_tests.py || goto :fail

echo === 2. Python reference model ===
py tools\ref_model.py || goto :fail

echo === 3. Verilator RTL regression ===
where verilator >nul 2>nul
if errorlevel 1 (
  echo Verilator not found. Install it or run this step in WSL/Linux.
) else (
  py scripts\run_verilator.py || goto :fail
)

echo === 4. Vivado early 25 MHz OOC implementation ===
where vivado >nul 2>nul
if errorlevel 1 (
  echo Vivado command not found in PATH. Open a Vivado command shell and run:
  echo vivado -mode batch -source vivado\run_ooc.tcl
) else (
  vivado -mode batch -source vivado\run_ooc.tcl || goto :fail
)

echo === DONE ===
exit /b 0

:fail
echo === FAILED: see messages above ===
exit /b 1
