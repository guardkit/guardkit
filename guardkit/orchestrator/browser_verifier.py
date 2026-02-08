"""BrowserVerifier abstraction for hiding browser tool selection.

Provides a unified interface for browser verification that abstracts
the choice between agent-browser (token-efficient) and Playwright/Appium
(for MAUI platform-specific targets).

Token Efficiency:
- AgentBrowserVerifier: ~1,400 tokens/cycle (5.7x more efficient)
- PlaywrightAppiumVerifier: ~7,800 tokens/cycle

Architecture:
- Coach agent never knows which browser tool is being used
- Only interacts via BrowserVerifier interface
- Orchestrator selects implementation based on target_stack and platform_target
"""

import asyncio
import json
import logging
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# ============================================================================
# Exceptions
# ============================================================================


class BrowserVerifierError(Exception):
    """Base exception for browser verifier errors."""

    pass


class AgentBrowserNotInstalledError(BrowserVerifierError):
    """Raised when agent-browser CLI is not installed."""

    pass


# ============================================================================
# Abstract Base Class
# ============================================================================


class BrowserVerifier(ABC):
    """Abstract base class for browser verification.

    Provides interface for:
    - Opening URLs
    - Taking screenshots (returns bytes for SSIM comparison)
    - Getting accessibility tree
    - Cleanup/close

    Implementations:
    - AgentBrowserVerifier: Primary (token-efficient)
    - PlaywrightAppiumVerifier: Fallback for MAUI iOS/Android
    """

    @abstractmethod
    async def open(self, url: str) -> None:
        """Open a URL in the browser.

        Args:
            url: The URL to open

        Raises:
            BrowserVerifierError: If opening URL fails
        """
        pass

    @abstractmethod
    async def screenshot(self, selector: Optional[str] = None) -> bytes:
        """Take screenshot, optionally of specific element.

        Args:
            selector: Optional element selector
                - For AgentBrowser: element ref (e.g., "@e1")
                - For Playwright: CSS selector (e.g., "#submit-btn")

        Returns:
            Screenshot as bytes suitable for SSIM comparison

        Raises:
            BrowserVerifierError: If screenshot fails
        """
        pass

    @abstractmethod
    async def get_accessibility_tree(self) -> List[Dict]:
        """Get accessibility tree for element inspection.

        Returns:
            List of accessibility nodes with structure:
            [
                {"ref": "@e1", "role": "button", "name": "Submit"},
                {"ref": "@e2", "role": "textbox", "name": "Email"}
            ]

        Raises:
            BrowserVerifierError: If tree extraction fails
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close browser and cleanup resources.

        Should be called when verification is complete to free resources.
        Must handle graceful cleanup even if browser not fully initialized.
        """
        pass


# ============================================================================
# AgentBrowserVerifier (Primary)
# ============================================================================


class AgentBrowserVerifier(BrowserVerifier):
    """Browser verifier using agent-browser CLI (~1,400 tokens/cycle).

    Primary implementation for all web targets.
    Uses element refs (@e1, @e2) instead of CSS selectors.

    Installation:
        npm install -g @anthropic/agent-browser

    Token Efficiency:
        5.7x more efficient than Playwright/Appium approach
    """

    def __init__(self):
        """Initialize AgentBrowserVerifier.

        Raises:
            AgentBrowserNotInstalledError: If agent-browser CLI not installed
        """
        self._process: Optional[subprocess.Popen] = None
        self._browser_url: Optional[str] = None
        self._verify_installation()

    def _verify_installation(self) -> None:
        """Check if agent-browser is installed.

        Raises:
            AgentBrowserNotInstalledError: If agent-browser CLI not installed
        """
        try:
            result = subprocess.run(
                ["agent-browser", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                logger.info(f"agent-browser installed: {result.stdout.strip()}")
            else:
                raise AgentBrowserNotInstalledError(
                    "agent-browser CLI is not installed or not accessible"
                )
        except FileNotFoundError:
            raise AgentBrowserNotInstalledError(
                "agent-browser CLI is not installed. "
                "Install with: npm install -g @anthropic/agent-browser"
            )
        except subprocess.TimeoutExpired:
            raise AgentBrowserNotInstalledError(
                "agent-browser CLI verification timed out"
            )

    async def open(self, url: str) -> None:
        """Open a URL in the browser.

        Args:
            url: The URL to open

        Raises:
            BrowserVerifierError: If opening URL fails
        """
        try:
            self._browser_url = url
            # Use subprocess to launch agent-browser
            # In production, this would use the actual CLI API
            result = subprocess.run(
                ["agent-browser", "open", url],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                raise BrowserVerifierError(
                    f"Failed to open URL: {result.stderr or result.stdout}"
                )
            logger.info(f"Opened URL in agent-browser: {url}")
        except subprocess.TimeoutExpired:
            raise BrowserVerifierError(f"Timeout opening URL: {url}")
        except Exception as e:
            raise BrowserVerifierError(f"Failed to open URL: {e}")

    async def screenshot(self, selector: Optional[str] = None) -> bytes:
        """Take screenshot, optionally of specific element.

        Args:
            selector: Optional element ref (e.g., "@e1")

        Returns:
            Screenshot as bytes

        Raises:
            BrowserVerifierError: If screenshot fails
        """
        try:
            cmd = ["agent-browser", "screenshot"]
            if selector:
                cmd.extend(["--selector", selector])

            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=30,
            )
            if result.returncode != 0:
                raise BrowserVerifierError(
                    f"Screenshot failed: {result.stderr.decode()}"
                )

            # Return the raw bytes from stdout
            return result.stdout if isinstance(result.stdout, bytes) else result.stdout.encode()

        except subprocess.TimeoutExpired:
            raise BrowserVerifierError("Screenshot timed out")
        except Exception as e:
            raise BrowserVerifierError(f"Screenshot failed: {e}")

    async def get_accessibility_tree(self) -> List[Dict]:
        """Get accessibility tree for element inspection.

        Returns:
            List of accessibility nodes

        Raises:
            BrowserVerifierError: If tree extraction fails
        """
        try:
            result = subprocess.run(
                ["agent-browser", "accessibility"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                raise BrowserVerifierError(
                    f"Failed to get accessibility tree: {result.stderr}"
                )

            # Parse JSON response
            tree = json.loads(result.stdout)
            return tree if isinstance(tree, list) else []

        except subprocess.TimeoutExpired:
            raise BrowserVerifierError("Accessibility tree extraction timed out")
        except json.JSONDecodeError as e:
            raise BrowserVerifierError(f"Invalid accessibility tree JSON: {e}")
        except Exception as e:
            raise BrowserVerifierError(f"Failed to get accessibility tree: {e}")

    async def close(self) -> None:
        """Close browser and cleanup resources.

        Gracefully handles cleanup even if browser not fully initialized.
        """
        try:
            if self._process and self._process.poll() is None:
                # Process is still running
                self._process.terminate()
                try:
                    self._process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._process.kill()
                logger.info("Terminated agent-browser process")

            # Clean shutdown via CLI
            subprocess.run(
                ["agent-browser", "close"],
                capture_output=True,
                timeout=5,
            )
        except Exception as e:
            # Log but don't raise - cleanup should be best-effort
            logger.warning(f"Error during cleanup: {e}")


# ============================================================================
# PlaywrightAppiumVerifier (Fallback)
# ============================================================================


class PlaywrightAppiumVerifier(BrowserVerifier):
    """Browser verifier for MAUI platform targets (~7,800 tokens/cycle).

    Fallback for iOS Simulator and Android Emulator.
    Uses Playwright MCP + Appium for platform-specific testing.

    Only activated for:
    - target_stack="maui" AND platform_target="ios"
    - target_stack="maui" AND platform_target="android"
    """

    def __init__(self, platform_target: str):
        """Initialize PlaywrightAppiumVerifier.

        Args:
            platform_target: Platform to target ("ios" or "android")
        """
        self.platform_target = platform_target
        self._browser = None
        self._context = None
        self._page = None

    async def _launch_appium(self) -> None:
        """Launch Appium session for the platform target.

        This is a placeholder for actual Appium/Playwright integration.
        In production, this would initialize Playwright with Appium.
        """
        # Placeholder - actual implementation would use Playwright + Appium
        logger.info(f"Launching Appium for {self.platform_target}")

    async def _capture_screenshot(self) -> bytes:
        """Capture screenshot via Playwright.

        This is a placeholder for actual Playwright screenshot API.
        """
        # Placeholder - actual implementation would use Playwright API
        return b"\x89PNG\r\n\x1a\n" + b"playwright screenshot"

    async def _extract_accessibility_tree(self) -> List[Dict]:
        """Extract accessibility tree via Playwright.

        This is a placeholder for actual Playwright accessibility API.
        """
        # Placeholder - actual implementation would use Playwright API
        return [
            {"role": "button", "name": "Submit", "selector": "#submit-btn"},
            {"role": "textbox", "name": "Email", "selector": "#email"},
        ]

    async def open(self, url: str) -> None:
        """Open a URL in the browser.

        Args:
            url: The URL to open

        Raises:
            BrowserVerifierError: If opening URL fails
        """
        try:
            await self._launch_appium()
            # Placeholder - actual implementation would navigate to URL
            logger.info(f"Opened URL via Playwright/Appium: {url}")
        except Exception as e:
            raise BrowserVerifierError(f"Failed to open URL: {e}")

    async def screenshot(self, selector: Optional[str] = None) -> bytes:
        """Take screenshot, optionally of specific element.

        Args:
            selector: Optional CSS selector (e.g., "#submit-btn")

        Returns:
            Screenshot as bytes

        Raises:
            BrowserVerifierError: If screenshot fails
        """
        try:
            return await self._capture_screenshot()
        except Exception as e:
            raise BrowserVerifierError(f"Screenshot failed: {e}")

    async def get_accessibility_tree(self) -> List[Dict]:
        """Get accessibility tree for element inspection.

        Returns:
            List of accessibility nodes

        Raises:
            BrowserVerifierError: If tree extraction fails
        """
        try:
            return await self._extract_accessibility_tree()
        except Exception as e:
            raise BrowserVerifierError(f"Failed to get accessibility tree: {e}")

    async def close(self) -> None:
        """Close browser and cleanup resources.

        Gracefully handles cleanup even if browser not fully initialized.
        """
        try:
            if self._page:
                await self._page.close()
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            logger.info("Closed Playwright/Appium session")
        except Exception as e:
            # Log but don't raise - cleanup should be best-effort
            logger.warning(f"Error during cleanup: {e}")


# ============================================================================
# Factory Function
# ============================================================================


def select_verifier(
    target_stack: str, platform_target: Optional[str] = None
) -> BrowserVerifier:
    """Factory function to select appropriate browser verifier.

    Selection logic:
    - MAUI + iOS/Android → PlaywrightAppiumVerifier (platform-specific)
    - Everything else → AgentBrowserVerifier (token-efficient default)

    Args:
        target_stack: Technology stack (e.g., 'react', 'maui')
        platform_target: Platform target for MAUI ('ios', 'android', 'web', None)

    Returns:
        Appropriate BrowserVerifier implementation

    Raises:
        AgentBrowserNotInstalledError: If agent-browser selected but not installed

    Examples:
        >>> verifier = select_verifier("react")
        >>> isinstance(verifier, AgentBrowserVerifier)
        True

        >>> verifier = select_verifier("maui", "ios")
        >>> isinstance(verifier, PlaywrightAppiumVerifier)
        True

        >>> verifier = select_verifier("maui", "web")
        >>> isinstance(verifier, AgentBrowserVerifier)
        True
    """
    # Use Playwright/Appium only for MAUI platform-specific targets
    if target_stack == "maui" and platform_target not in (None, "web"):
        logger.info(
            f"Selected PlaywrightAppiumVerifier for {target_stack}/{platform_target}"
        )
        return PlaywrightAppiumVerifier(platform_target)

    # Default to agent-browser for all web targets (5.7x more token-efficient)
    logger.info(f"Selected AgentBrowserVerifier for {target_stack}")
    return AgentBrowserVerifier()
