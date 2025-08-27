#!/usr/bin/env python3
"""
Script to create initial database migration
"""
import subprocess
import sys
import os

def run_command(command):
    """Run a shell command and return the result"""
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {command}")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {command}")
        print(f"Error: {e.stderr}")
        return False

def main():
    """Create initial migration"""
    print("Creating initial database migration...")
    
    # Change to backend directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Create initial migration
    if not run_command("alembic revision --autogenerate -m 'Initial migration'"):
        sys.exit(1)
    
    print("\n✅ Initial migration created successfully!")
    print("To apply the migration, run: alembic upgrade head")

if __name__ == "__main__":
    main()