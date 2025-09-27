#!/usr/bin/env python3
"""
Test runner script for SallyBot API tests.
"""
import subprocess
import sys
import os

def run_tests():
    """Run the test suite."""
    print("🚀 Running SallyBot API Tests")
    print("=" * 50)

    # Change to the backend directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # Run pytest with coverage
    cmd = [
        "python", "-m", "pytest",
        "--cov=app",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov",
        "-v",
        "tests/"
    ]

    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except KeyboardInterrupt:
        print("\n❌ Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return 1

def run_specific_test(test_file):
    """Run a specific test file."""
    print(f"🎯 Running specific test: {test_file}")
    print("=" * 50)

    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    cmd = [
        "python", "-m", "pytest",
        "-v",
        f"tests/{test_file}"
    ]

    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except KeyboardInterrupt:
        print("\n❌ Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return 1

if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_file = sys.argv[1]
        exit_code = run_specific_test(test_file)
    else:
        exit_code = run_tests()

    sys.exit(exit_code)
