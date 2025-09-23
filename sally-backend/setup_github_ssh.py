#!/usr/bin/env python3
"""
Setup GitHub SSH authentication for Docs-as-Code system.
This script helps configure SSH key authentication to avoid repeated logins.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GitHubSSHSetup:
    """Setup SSH authentication for GitHub."""

    def __init__(self):
        self.home = Path.home()
        self.ssh_dir = self.home / ".ssh"
        self.ssh_key_path = self.ssh_dir / "id_ed25519_sallybot"
        self.ssh_pub_key_path = self.ssh_dir / "id_ed25519_sallybot.pub"
        self.config_path = self.ssh_dir / "config"

    def check_ssh_installed(self) -> bool:
        """Check if SSH is installed."""
        try:
            result = subprocess.run(
                ["ssh", "-V"],
                capture_output=True,
                text=True,
                check=True
            )
            logger.info(f"SSH version: {result.stderr.strip()}")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.error("SSH is not installed. Please install OpenSSH client.")
            return False

    def check_existing_keys(self) -> bool:
        """Check if SSH keys already exist."""
        if self.ssh_key_path.exists():
            logger.info(f"SSH key already exists at: {self.ssh_key_path}")
            return True
        return False

    def generate_ssh_key(self, email: str) -> bool:
        """Generate new SSH key pair."""
        try:
            logger.info("Generating new SSH key pair...")

            # Create .ssh directory if it doesn't exist
            self.ssh_dir.mkdir(mode=0o700, exist_ok=True)

            # Generate key
            cmd = [
                "ssh-keygen",
                "-t", "ed25519",
                "-C", email,
                "-f", str(self.ssh_key_path),
                "-N", ""  # No passphrase
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            logger.info("SSH key generated successfully!")
            logger.info(f"Private key: {self.ssh_key_path}")
            logger.info(f"Public key: {self.ssh_pub_key_path}")

            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to generate SSH key: {e.stderr}")
            return False

    def get_public_key_content(self) -> Optional[str]:
        """Get the public key content."""
        try:
            with open(self.ssh_pub_key_path, 'r') as f:
                return f.read().strip()
        except FileNotFoundError:
            logger.error(f"Public key file not found: {self.ssh_pub_key_path}")
            return None

    def setup_ssh_config(self) -> bool:
        """Setup SSH config for GitHub."""
        try:
            config_content = f"""# GitHub SSH configuration for SallyBot
Host github.com
    HostName github.com
    User git
    IdentityFile {self.ssh_key_path}
    IdentitiesOnly yes
"""

            # Read existing config if it exists
            existing_config = ""
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    existing_config = f.read()

            # Check if GitHub config already exists
            if "Host github.com" in existing_config:
                logger.info("GitHub SSH config already exists")
                return True

            # Append new config
            with open(self.config_path, 'a') as f:
                f.write(config_content)

            # Set correct permissions (skip on Windows, handled separately)
            try:
                self.config_path.chmod(0o600)
            except OSError:
                logger.warning("Could not set file permissions (might be on Windows)")

            logger.info("SSH config updated successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to setup SSH config: {e}")
            return False

    def test_ssh_connection(self) -> bool:
        """Test SSH connection to GitHub."""
        try:
            logger.info("Testing SSH connection to GitHub...")

            # Test connection (this will fail with permission denied if key not added to GitHub)
            cmd = [
                "ssh",
                "-T",
                "git@github.com",
                "-o", "StrictHostKeyChecking=no",
                "-o", "ConnectTimeout=10"
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=15
            )

            if "successfully authenticated" in result.stderr:
                logger.info("SSH connection test successful!")
                return True
            elif "Permission denied" in result.stderr:
                logger.warning("SSH key not added to GitHub account yet")
                logger.info("Please add the public key to your GitHub account:")
                logger.info("1. Copy the public key below:")
                pub_key = self.get_public_key_content()
                if pub_key:
                    print(f"\n{pub_key}\n")
                logger.info("2. Go to https://github.com/settings/keys")
                logger.info("3. Click 'New SSH key'")
                logger.info("4. Paste the key and save")
                return False
            else:
                logger.error(f"SSH test failed: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("SSH connection test timed out")
            return False
        except Exception as e:
            logger.error(f"SSH test failed: {e}")
            return False

    def update_git_config(self, repo_url: str) -> str:
        """Convert HTTPS URL to SSH URL."""
        if repo_url.startswith("https://github.com/"):
            # Convert HTTPS to SSH
            ssh_url = repo_url.replace("https://github.com/", "git@github.com:")
            logger.info(f"Converted URL to SSH: {ssh_url}")
            return ssh_url
        elif repo_url.startswith("git@github.com:"):
            logger.info("URL is already SSH format")
            return repo_url
        else:
            logger.warning(f"Unknown URL format: {repo_url}")
            return repo_url


def main():
    """Main setup function."""
    print("🔧 راه‌اندازی اتصال SSH به GitHub برای SallyBot")
    print("=" * 50)

    setup = GitHubSSHSetup()

    # Check SSH installation
    if not setup.check_ssh_installed():
        return

    # Check existing keys
    if setup.check_existing_keys():
        print("✅ SSH key already exists")
    else:
        # Generate new key
        email = input("Enter your GitHub email address: ").strip()
        if not email:
            logger.error("Email is required")
            return

        if not setup.generate_ssh_key(email):
            return

    # Setup SSH config
    if not setup.setup_ssh_config():
        return

    # Get public key for user
    pub_key = setup.get_public_key_content()
    if pub_key:
        print("\n" + "="*50)
        print("🔑 PUBLIC KEY - کپی کنید و به GitHub اضافه کنید:")
        print("="*50)
        print(pub_key)
        print("="*50)
        print("\n📋 مراحل اضافه کردن به GitHub:")
        print("1. به https://github.com/settings/keys بروید")
        print("2. روی 'New SSH key' کلیک کنید")
        print("3. یک نام برای key انتخاب کنید (مثل 'SallyBot Server')")
        print("4. کلید بالا را paste کنید")
        print("5. روی 'Add SSH key' کلیک کنید")
        print("\nپس از اضافه کردن کلید، Enter را فشار دهید تا تست کنیم...")

        input("کلید را به GitHub اضافه کنید و Enter را فشار دهید...")

    # Test connection
    if setup.test_ssh_connection():
        print("✅ همه چیز آماده است!")
        print("\n🔄 حالا باید تنظیمات Git را تغییر دهید:")
        print("فایل .env را باز کنید و این تغییرات را اعمال کنید:")
        print("- KB_GIT_REPO_URL را به آدرس SSH تغییر دهید")
        print("- KB_GIT_USERNAME و KB_GIT_PASSWORD را حذف کنید")
        print("\nمثال:")
        print('KB_GIT_REPO_URL="git@github.com:your-username/knowledge-base.git"')
    else:
        print("❌ اتصال SSH هنوز برقرار نیست. لطفاً مراحل بالا را دوباره بررسی کنید.")


if __name__ == "__main__":
    main()
