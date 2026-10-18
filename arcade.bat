@echo off
chcp 65001 >nul
title Retro Terminal Arcade TUI
python "%~dp0arcade.py" %*
