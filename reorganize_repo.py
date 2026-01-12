"""
Repository Reorganization Script
Cleans and organizes the OI-7500 pipeline repository.
"""

import os
import shutil
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent

# Define new structure
ARCHIVE_DIR = BASE_DIR / "archive"
REFERENCE_DIR = BASE_DIR / "reference"
TOOLS_DIR = BASE_DIR / "tools"

# Create directories
print("Creating new directory structure...")
(ARCHIVE_DIR / "test_scripts").mkdir(parents=True, exist_ok=True)
(ARCHIVE_DIR / "analysis").mkdir(parents=True, exist_ok=True)
(ARCHIVE_DIR / "experiments").mkdir(parents=True, exist_ok=True)
(ARCHIVE_DIR / "old_monitors").mkdir(parents=True, exist_ok=True)
(ARCHIVE_DIR / "deprecated_docs").mkdir(parents=True, exist_ok=True)

(REFERENCE_DIR / "protocol").mkdir(parents=True, exist_ok=True)
(REFERENCE_DIR / "hardware").mkdir(parents=True, exist_ok=True)

TOOLS_DIR.mkdir(exist_ok=True)

# Files to keep in root (active production scripts)
KEEP_IN_ROOT = {
    'network_monitor_with_ha.py',  # Will rename to monitor.py
    'config.yaml',
    'requirements.txt',
    'pytest.ini',
    '.gitignore',
    'README.md',  # Will be replaced with new comprehensive version
}

# Files to move to tools/
MOVE_TO_TOOLS = {
    'configure_radio.py',
    'decode_packet.py', 
    'manual_decode.py',
    'get_channel_psk.py',
    'hardware_test.py',
}

# Directories to keep as-is
KEEP_DIRS = {
    'pipeline',
    'configs',
    'logs',
    'test',
    '.venv',
    '.git',
    'archive',
    'reference',
    'tools',
}

# Archive patterns
ARCHIVE_PATTERNS = {
    'test_scripts': lambda f: f.startswith('test_') and f.endswith('.py'),
    'analysis': lambda f: f.startswith('analyze_') and f.endswith('.py'),
    'experiments': lambda f: any(f.startswith(p) for p in ['capture_', 'scan_', 'probe_', 'find_', 'search_', 'verify_', 'validate_']),
    'old_monitors': lambda f: any(x in f for x in ['monitor', 'laird_monitor', 'simple_monitor']) and f not in KEEP_IN_ROOT,
}

def should_skip(path: Path) -> bool:
    """Check if file/dir should be skipped."""
    if path.name.startswith('.'):
        return True
    if path.name in KEEP_DIRS:
        return True
    if path.is_file() and path.name in KEEP_IN_ROOT:
        return True
    if path.is_file() and path.name in MOVE_TO_TOOLS:
        return True
    if path.name == 'reorganize_repo.py':
        return True
    return False

def get_archive_destination(filename: str) -> Path:
    """Determine which archive subdirectory a file belongs to."""
    for subdir, pattern_func in ARCHIVE_PATTERNS.items():
        if pattern_func(filename):
            return ARCHIVE_DIR / subdir / filename
    # Default: put other .py files in experiments
    if filename.endswith('.py'):
        return ARCHIVE_DIR / "experiments" / filename
    # Markdown files
    if filename.endswith('.md') and filename not in KEEP_IN_ROOT:
        return ARCHIVE_DIR / "deprecated_docs" / filename
    return None

def move_file(src: Path, dst: Path):
    """Safely move a file."""
    if dst.exists():
        print(f"  SKIP (exists): {src.name} → {dst}")
        return
    print(f"  MOVE: {src.name} → {dst}")
    shutil.move(str(src), str(dst))

def main():
    print("=" * 70)
    print("OI-7500 REPOSITORY REORGANIZATION")
    print("=" * 70)
    print()
    
    # Get all root-level files
    root_files = [f for f in BASE_DIR.iterdir() if f.is_file() and not should_skip(f)]
    
    print(f"Found {len(root_files)} files to process")
    print()
    
    # Move tools
    print("Moving utility scripts to tools/...")
    for filename in MOVE_TO_TOOLS:
        src = BASE_DIR / filename
        if src.exists():
            dst = TOOLS_DIR / filename
            move_file(src, dst)
    print()
    
    # Archive old files
    print("Archiving old/test files...")
    archived_count = 0
    for file_path in root_files:
        if file_path.name in MOVE_TO_TOOLS:
            continue
        
        dst = get_archive_destination(file_path.name)
        if dst:
            move_file(file_path, dst)
            archived_count += 1
    
    print(f"\nArchived {archived_count} files")
    print()
    
    # Rename main monitor
    print("Renaming main monitor script...")
    old_name = BASE_DIR / "network_monitor_with_ha.py"
    new_name = BASE_DIR / "monitor.py"
    if old_name.exists():
        print(f"  RENAME: network_monitor_with_ha.py → monitor.py")
        shutil.move(str(old_name), str(new_name))
    print()
    
    print("=" * 70)
    print("REORGANIZATION COMPLETE")
    print("=" * 70)
    print()
    print("Summary:")
    print(f"  - Active scripts: {len(KEEP_IN_ROOT)} files")
    print(f"  - Tools: {len([f for f in TOOLS_DIR.iterdir() if f.is_file()])} utilities")
    print(f"  - Archived: {archived_count} files")
    print()
    print("Next steps:")
    print("  1. Review the archive/ directory")
    print("  2. Create comprehensive README.md")
    print("  3. Add protocol documentation to reference/")
    print("  4. Test monitor.py still works")
    print()

if __name__ == "__main__":
    main()
