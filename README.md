# OrcaSlicer Post-Processing Script

Adds timelapse capture commands to G-code for automatic layer change detection.

## Setup

1. In OrcaSlicer, go to Print Settings → Output Options
2. Set Post-processing Scripts to this file
3. Save settings

## How It Works

- Adds "M118 Smile" command before each layer change
- Printer sends "Smile" message when reaching these commands
- Main application captures screenshot on "Smile" detection