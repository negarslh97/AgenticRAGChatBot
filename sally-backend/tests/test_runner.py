#!/usr/bin/env python3
"""
Test runner script for SallyBot tests
Provides convenient commands to run different test suites
"""

import sys
import subprocess
from pathlib import Path


def run_command(cmd: list) -> int:
    """Run a command and return exit code."""
    print(f"Running: {' '.join(cmd)}")
    print("=" * 80)
    result = subprocess.run(cmd)
    print("=" * 80)
    return result.returncode


def main():
    """Main test runner."""
    if len(sys.argv) < 2:
        print("""
SallyBot Test Runner
====================

Usage: python test_runner.py [command]

Commands:
  all                 - Run all tests
  unit                - Run unit tests only
  integration         - Run integration tests only
  weaviate            - Run Weaviate tests
  mongodb             - Run MongoDB tests
  rag                 - Run RAG service tests
  coverage            - Run tests with coverage report
  fast                - Run fast tests (exclude slow)
  
Examples:
  python test_runner.py unit
  python test_runner.py integration
  python test_runner.py coverage
""")
        return 1
    
    command = sys.argv[1].lower()
    
    # Base pytest command
    base_cmd = ["pytest", "-v"]
    
    if command == "all":
        cmd = base_cmd
    
    elif command == "unit":
        cmd = base_cmd + ["-m", "unit"]
    
    elif command == "integration":
        cmd = base_cmd + ["-m", "integration"]
    
    elif command == "weaviate":
        cmd = base_cmd + ["-m", "weaviate"]
    
    elif command == "mongodb":
        cmd = base_cmd + ["-m", "mongodb"]
    
    elif command == "rag":
        cmd = base_cmd + ["tests/test_rag_service.py"]
    
    elif command == "coverage":
        cmd = ["pytest", "--cov=app", "--cov-report=html", "--cov-report=term"]
    
    elif command == "fast":
        cmd = base_cmd + ["-m", "not slow"]
    
    else:
        print(f"Unknown command: {command}")
        return 1
    
    # Run the command
    return run_command(cmd)


if __name__ == "__main__":
    sys.exit(main())
