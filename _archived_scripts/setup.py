"""
Setup script for SpaceIQ Bot

Automated setup and dependency installation.
"""

import subprocess
import sys
import os
from pathlib import Path


def run_command(command, description):
    """Run a command and handle errors"""
    print(f"\n⏳ {description}...")
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )
        print(f"✅ {description} - Done")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - Failed")
        print(f"Error: {e.stderr}")
        return False


def main():
    """Main setup function"""

    print("\n" + "=" * 70)
    print("SpaceIQ Bot - Setup Script")
    print("=" * 70 + "\n")

    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        sys.exit(1)

    print(f"✅ Python version: {sys.version.split()[0]}")

    # Install Python dependencies
    if not run_command(
        "pip install -r requirements.txt",
        "Installing Python dependencies"
    ):
        sys.exit(1)

    # Install Playwright browsers
    if not run_command(
        "playwright install chromium",
        "Installing Playwright Chromium browser"
    ):
        sys.exit(1)

    # Create .env file if it doesn't exist
    env_file = Path(".env")
    env_example = Path(".env.example")

    if not env_file.exists() and env_example.exists():
        print("\n⏳ Creating .env file from template...")
        env_file.write_text(env_example.read_text())
        print("✅ .env file created")
        print("\n⚠️  IMPORTANT: Edit .env and set your SPACEIQ_URL")
    elif env_file.exists():
        print("\n✅ .env file already exists")
    else:
        print("\n⚠️  .env.example not found")

    # Create necessary directories
    print("\n⏳ Creating directories...")
    Path("playwright/.auth").mkdir(parents=True, exist_ok=True)
    Path("screenshots").mkdir(parents=True, exist_ok=True)
    print("✅ Directories created")

    # Final instructions
    print("\n" + "=" * 70)
    print("✅ Setup Complete!")
    print("=" * 70)
    print("\nNext steps:")
    print("\n1. Edit .env file:")
    print("   - Set SPACEIQ_URL to your SpaceIQ instance URL")
    print("\n2. Capture your authentication session:")
    print("   python src/auth/capture_session.py")
    print("\n3. Run the bot:")
    print("   python main.py")
    print("\n" + "=" * 70 + "\n")


if __name__ == "__main__":
    main()
