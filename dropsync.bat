@echo off
title DropSync Pro Controller
cd /d "%~dp0"
start "" pyw controller.py || start "" py controller.py
exit
