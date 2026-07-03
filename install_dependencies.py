#!/usr/bin/env python3
"""
Plex TrueShuffle Dependencies Installer
This script installs all required dependencies for the Plex TrueShuffle script.
"""

import subprocess
import sys
import os

def install_package(package):
    """Install a Python package using pip."""
    try:
        print(f"Installing {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✅ {package} installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install {package}: {e}")
        return False

def check_package(package):
    """Check if a package is already installed."""
    try:
        __import__(package)
        return True
    except ImportError:
        return False

def main():
    print("🔧 Plex TrueShuffle Dependencies Installer")
    print("=" * 50)
    
    # List of required packages
    required_packages = [
        "plexapi>=4.15.0",
        "psutil>=5.9.0"
    ]
    
    # List of optional packages for enhanced features
    optional_packages = [
        "memory-profiler>=0.60.0"
    ]
    
    print("📋 Required packages:")
    for package in required_packages:
        package_name = package.split('>=')[0]
        if check_package(package_name):
            print(f"  ✅ {package} - Already installed")
        else:
            print(f"  ⏳ {package} - Needs installation")
    
    print("\n📋 Optional packages (for enhanced features):")
    for package in optional_packages:
        package_name = package.split('>=')[0]
        if check_package(package_name):
            print(f"  ✅ {package} - Already installed")
        else:
            print(f"  ⏳ {package} - Needs installation")
    
    print("\n🚀 Starting installation...")
    
    # Install required packages
    failed_installations = []
    
    for package in required_packages:
        package_name = package.split('>=')[0]
        if not check_package(package_name):
            if not install_package(package):
                failed_installations.append(package)
    
    # Ask about optional packages
    print("\n❓ Would you like to install optional packages for enhanced features? (y/n): ", end="")
    try:
        choice = input().strip().lower()
        if choice in ['y', 'yes']:
            print("\n📦 Installing optional packages...")
            for package in optional_packages:
                package_name = package.split('>=')[0]
                if not check_package(package_name):
                    install_package(package)
    except KeyboardInterrupt:
        print("\n⏹️ Installation of optional packages cancelled.")
    
    # Final status
    print("\n📊 Installation Summary:")
    print("=" * 30)
    
    all_packages = required_packages + optional_packages
    installed_count = 0
    
    for package in all_packages:
        package_name = package.split('>=')[0]
        if check_package(package_name):
            installed_count += 1
            print(f"✅ {package_name} - Installed")
        else:
            print(f"❌ {package_name} - Not installed")
    
    print(f"\n📈 Successfully installed: {installed_count}/{len(all_packages)} packages")
    
    if failed_installations:
        print(f"\n⚠️ Failed installations: {len(failed_installations)}")
        print("You may need to install these manually:")
        for package in failed_installations:
            print(f"  pip install {package}")
    
    if installed_count == len(required_packages):
        print("\n🎉 All required dependencies are installed!")
        print("💡 You can now run the Plex TrueShuffle script.")
    else:
        print("\n⚠️ Some required dependencies are missing.")
        print("💡 Please install the missing packages before running the script.")
    
    print("\n📚 For more information, see requirements.txt")

if __name__ == "__main__":
    main() 