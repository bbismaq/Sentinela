#!/usr/bin/env bash
# Sentinela installer launcher for macOS.
# Double-click this file in Finder. It opens Terminal and runs install.sh.

cd "$(dirname "$0")"
echo ""
echo "============================================"
echo "  Sentinela - macOS Installer"
echo "============================================"
echo ""

bash ./install.sh
status=$?

echo ""
if [ $status -eq 0 ]; then
    echo "Installation finished. You can close this window."
else
    echo "Installation failed with code $status. Read the messages above."
fi
echo ""
read -n 1 -s -r -p "Press any key to close..."
echo ""
