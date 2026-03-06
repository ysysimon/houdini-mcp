"""Tests for viewport handlers."""
import sys
import os
import types

import pytest

if "hou" not in sys.modules:
    pytest.skip("hou mock not loaded", allow_module_level=True)

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from houdinimcp.handlers.viewport import (
    list_panes, set_current_network,
)


class TestViewportHandlers:
    def setup_method(self):
        self._orig_ui = sys.modules["hou"].ui
        self._orig_node = sys.modules["hou"].node

    def teardown_method(self):
        sys.modules["hou"].ui = self._orig_ui
        sys.modules["hou"].node = self._orig_node

    def test_list_panes(self):
        tab1 = types.SimpleNamespace(
            name=lambda: "viewer1",
            type=lambda: "SceneViewer",
            isCurrentTab=lambda: True,
        )
        sys.modules["hou"].ui = types.SimpleNamespace(
            paneTabs=lambda: [tab1],
            paneTabOfType=lambda t: None,
        )
        result = list_panes()
        assert result["count"] == 1
        assert result["panes"][0]["name"] == "viewer1"

    def test_list_panes_empty(self):
        sys.modules["hou"].ui = types.SimpleNamespace(
            paneTabs=lambda: [],
            paneTabOfType=lambda t: None,
        )
        result = list_panes()
        assert result["count"] == 0

    def test_set_current_network(self):
        node = types.SimpleNamespace(path=lambda: "/obj/geo1")
        editor = types.SimpleNamespace(setCurrentNode=lambda n: None)
        sys.modules["hou"].ui = types.SimpleNamespace(
            paneTabOfType=lambda t: editor,
            paneTabs=lambda: [],
        )
        sys.modules["hou"].paneTabType = types.SimpleNamespace(
            NetworkEditor=1, SceneViewer=0,
        )
        sys.modules["hou"].node = lambda p: node if p == "/obj/geo1" else None
        result = set_current_network("/obj/geo1")
        assert result["path"] == "/obj/geo1"

    def test_set_current_network_not_found(self):
        editor = types.SimpleNamespace(setCurrentNode=lambda n: None)
        sys.modules["hou"].ui = types.SimpleNamespace(
            paneTabOfType=lambda t: editor,
            paneTabs=lambda: [],
        )
        sys.modules["hou"].paneTabType = types.SimpleNamespace(
            NetworkEditor=1, SceneViewer=0,
        )
        sys.modules["hou"].node = lambda p: None
        with pytest.raises(ValueError, match="Node not found"):
            set_current_network("/obj/missing")
