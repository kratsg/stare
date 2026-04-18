"""Tests for stare._output.stdout_is_interactive."""

from __future__ import annotations

import io
import os
import stat
import sys
from unittest.mock import patch

import pytest

from stare._output import stdout_is_interactive


class TestStdoutIsInteractive:
    def test_fifo_returns_false(self) -> None:
        """A pipe (FIFO) stdout should return False."""
        fake_stat = os.stat_result((stat.S_IFIFO | 0o600, 0, 0, 0, 0, 0, 0, 0, 0, 0))
        with patch("os.fstat", return_value=fake_stat):
            assert stdout_is_interactive() is False

    def test_regular_file_returns_false(self) -> None:
        """A regular file (redirect) stdout should return False."""
        fake_stat = os.stat_result((stat.S_IFREG | 0o600, 0, 0, 0, 0, 0, 0, 0, 0, 0))
        with patch("os.fstat", return_value=fake_stat):
            assert stdout_is_interactive() is False

    def test_char_device_tty_returns_true(self) -> None:
        """A character device (TTY) stdout should delegate to isatty()."""
        fake_stat = os.stat_result((stat.S_IFCHR | 0o600, 0, 0, 0, 0, 0, 0, 0, 0, 0))
        with (
            patch("os.fstat", return_value=fake_stat),
            patch.object(sys.stdout, "isatty", return_value=True),
        ):
            assert stdout_is_interactive() is True
        with (
            patch("os.fstat", return_value=fake_stat),
            patch.object(sys.stdout, "isatty", return_value=False),
        ):
            assert stdout_is_interactive() is False

    def test_fstat_oserror_falls_back_to_isatty(self) -> None:
        """When fstat raises OSError, fall back to isatty()."""
        with (
            patch("os.fstat", side_effect=OSError("no fd")),
            patch.object(sys.stdout, "isatty", return_value=True),
        ):
            assert stdout_is_interactive() is True
        with (
            patch("os.fstat", side_effect=OSError("no fd")),
            patch.object(sys.stdout, "isatty", return_value=False),
        ):
            assert stdout_is_interactive() is False

    def test_stringio_stdout_falls_back_to_isatty(self) -> None:
        """StringIO has no fileno(); the AttributeError triggers the fallback."""
        buf = io.StringIO()
        with patch.object(sys, "stdout", buf):
            # StringIO.isatty() returns False
            assert stdout_is_interactive() is False

    @pytest.mark.parametrize("exc_type", [OSError, ValueError, AttributeError])
    def test_various_fstat_exceptions_fall_back(self, exc_type: type) -> None:
        with (
            patch("os.fstat", side_effect=exc_type("boom")),
            patch.object(sys.stdout, "isatty", return_value=False),
        ):
            assert stdout_is_interactive() is False
