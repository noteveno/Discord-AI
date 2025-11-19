import subprocess
import sys
import os

def install_requirements():
    req_file = 'requirements.txt'
    
    if not os.path.exists(req_file):
        print(f"❌ Error: {req_file} not found!")
        return

    print(f"📦 Reading {req_file}...")
    
    with open(req_file, 'r') as f:
        packages = [line.strip() for line in f if line.strip() and not line.startswith('#')]

    if not packages:
        print("⚠️ No packages found in requirements.txt")
        return

    print(f"🚀 Found {len(packages)} packages to install.")
    
    failed = []
    success = []

    for package in packages:
        print(f"⏳ Installing {package}...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"✅ Successfully installed {package}")
            success.append(package)
        except subprocess.CalledProcessError:
            print(f"❌ Failed to install {package}")
            failed.append(package)
        except Exception as e:
            print(f"❌ Error installing {package}: {e}")
            failed.append(package)

    print("\n" + "="*30)
    print(f"🎉 Installation complete!")
    print(f"✅ Installed: {len(success)}")
    if failed:
        print(f"❌ Failed: {len(failed)}")
        for p in failed:
            print(f"   - {p}")
    else:
        print("✨ All packages installed successfully!")
    print("="*30)

if __name__ == "__main__":
    install_requirements()
