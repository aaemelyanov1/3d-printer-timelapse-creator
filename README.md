# 3D Printer Timelapse Creator

A comprehensive Python solution for creating stunning timelapse videos of 3D printing projects. Multiple interfaces for different user preferences and workflows.

## Repository Structure

This repository is organized into three main branches, each serving a specific purpose:

### 🌿 **Main Branch** (current)
- **Stable production code** - tested and ready-to-use versions
- **Complete project structure** - all components in one place
- **Documentation** - comprehensive guides and examples
- **Recommended for most users** - start here if you're unsure

### 🖥️ **Desktop-App Branch**
- **GUI application** - user-friendly desktop interface
- **Real-time camera preview** - see what your camera sees
- **Visual settings configuration** - no code editing required
- **Perfect for beginners** and those who prefer graphical interfaces

### ⌨️ **CLI-Script Branch** 
- **Command-line interface** - lightweight and efficient
- **Terminal-based operation** - ideal for headless systems (Raspberry Pi, etc.)
- **Automation-friendly** - easily integrated into scripts
- **Best for advanced users** and automated workflows

### 🔧 **OrcaSlicer-Script Branch**
- **G-code post-processing** - automatic integration with OrcaSlicer
- **Layer change detection** - adds capture commands to your print files
- **Seamless workflow** - no manual intervention during printing
- **Essential for automated** layer-by-layer timelapses

## Quick Start

### Option 1: Desktop Application (Recommended for Beginners)
```bash
cd desktop-app
pip install -r requirements.txt
python main.py
