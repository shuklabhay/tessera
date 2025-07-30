import subprocess
import sys
from pathlib import Path


def get_base_path() -> Path:
    """Returns the base project path."""
    return Path(__file__).parent.parent


def build_executable() -> bool:
    """Builds the macOS app bundle using PyInstaller."""
    base_path = get_base_path()
    spec_path = base_path / "Tessera.spec"

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--noconfirm",
        str(spec_path),
    ]

    result = subprocess.run(cmd, cwd=base_path, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"PyInstaller failed: {result.stderr}")
        return False

    return True


def main() -> bool:
    """Main build function."""
    if not build_executable():
        print("❌ Failed to build executable")
        return False

    print("🎉 Build completed successfully!")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
