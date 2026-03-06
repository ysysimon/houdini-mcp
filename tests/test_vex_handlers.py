"""Tests for VEX handlers."""
import sys
import os
import types

import pytest

if "hou" not in sys.modules:
    pytest.skip("hou mock not loaded", allow_module_level=True)

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))


def _setup_hou_text():
    hou = sys.modules["hou"]
    if not hasattr(hou, "text"):
        hou.text = types.SimpleNamespace(
            vexSyntaxCheck=lambda code: "" if "error" not in code else "Syntax error at line 1",
        )


class MockParm:
    def __init__(self, name, value=""):
        self._name = name
        self._value = value

    def name(self):
        return self._name

    def set(self, val):
        self._value = val

    def eval(self):
        return self._value


class MockCreatedNode:
    def __init__(self, name, path, node_type):
        self._name = name
        self._path = path
        self._type = node_type
        self._parms = {"snippet": MockParm("snippet"), "class": MockParm("class", 1)}

    def name(self):
        return self._name

    def path(self):
        return self._path

    def type(self):
        return types.SimpleNamespace(name=lambda: self._type)

    def parm(self, name):
        return self._parms.get(name)


class MockParentNode:
    def __init__(self, path):
        self._path = path
        self._created = None

    def path(self):
        return self._path

    def createNode(self, node_type, node_name=None):
        name = node_name or node_type
        self._created = MockCreatedNode(name, f"{self._path}/{name}", node_type)
        return self._created


from houdinimcp.handlers.vex import (
    create_wrangle, set_wrangle_code, get_wrangle_code,
    create_vex_expression, validate_vex,
)


class TestVexHandlers:
    def setup_method(self):
        _setup_hou_text()
        self._orig_node = sys.modules["hou"].node
        self.parent = MockParentNode("/obj/geo1")
        self.wrangle = MockCreatedNode("wrangle1", "/obj/geo1/wrangle1", "attribwrangle")
        nodes = {"/obj/geo1": self.parent, "/obj/geo1/wrangle1": self.wrangle}
        sys.modules["hou"].node = lambda p: nodes.get(p)

    def teardown_method(self):
        sys.modules["hou"].node = self._orig_node

    def test_create_wrangle(self):
        result = create_wrangle("/obj/geo1", code="@Cd = {1,0,0};")
        assert result["type"] == "attribwrangle"

    def test_set_wrangle_code(self):
        result = set_wrangle_code("/obj/geo1/wrangle1", "@P.y += 1;")
        assert result["code_length"] > 0
        assert self.wrangle._parms["snippet"]._value == "@P.y += 1;"

    def test_get_wrangle_code(self):
        self.wrangle._parms["snippet"]._value = "@P *= 2;"
        result = get_wrangle_code("/obj/geo1/wrangle1")
        assert result["code"] == "@P *= 2;"

    def test_create_vex_expression(self):
        result = create_vex_expression("/obj/geo1", "dist", "length(@P)")
        assert "@dist" in result["code"]

    def test_validate_vex_valid(self):
        result = validate_vex("@P.y += 1;")
        assert result["valid"] is True

    def test_validate_vex_invalid(self):
        # Override the global hou.text mock for this test
        sys.modules["hou"].text.vexSyntaxCheck = lambda code: "Syntax error at line 1" if "error" in code else ""
        result = validate_vex("error in code")
        assert result["valid"] is False
        # Restore
        sys.modules["hou"].text.vexSyntaxCheck = lambda code: ""

    def test_set_wrangle_node_not_found(self):
        sys.modules["hou"].node = lambda p: None
        with pytest.raises(ValueError, match="Node not found"):
            set_wrangle_code("/obj/missing", "code")

    def test_create_wrangle_parent_not_found(self):
        sys.modules["hou"].node = lambda p: None
        with pytest.raises(ValueError, match="Parent not found"):
            create_wrangle("/obj/missing")
