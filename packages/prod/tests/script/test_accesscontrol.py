"""Scripts of the OpenKNX AccessControl application (opt-in).

    XKNX_TEST_ACCESSCONTROL_KNXPROD=<path>/AccessControl.knxprod uv run pytest \\
        packages/prod/tests/script/test_accesscontrol.py -s
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from xknxeditor.prod import Archive
from xknxeditor.prod.application import Application, parse_application_xml
from xknxeditor.prod.parser_v2.dynamic import DynamicUI
from xknxeditor.prod.parser_v2.ui import UiButton, UiNode, UiParameterBlock, UiTab
from xknxeditor.prod.script import ParameterValidationError
from xknxeditor.prod.script.button import run_offline_button

_PATH = os.environ.get("XKNX_TEST_ACCESSCONTROL_KNXPROD")

pytestmark = pytest.mark.skipif(
    not _PATH, reason="XKNX_TEST_ACCESSCONTROL_KNXPROD not set"
)


@pytest.fixture(scope="module")
def app() -> Application:
    assert _PATH is not None
    with Archive(Path(_PATH)) as archive:
        (manufacturer,) = archive.manufacturer_ids
        xmls = archive.get_application_xmls(manufacturer)
        (xml,) = xmls.values()
    return parse_application_xml(xml, manufacturer, language="de-DE")[0]


@pytest.fixture
def ui(app: Application) -> DynamicUI:
    dui = DynamicUI(app.program, tree_builder=app.tree_builder())
    dui.ui()
    return dui


def _ref(ui: DynamicUI, name: str) -> str:
    ref = ui.find_parameter_ref("name", name)
    assert ref is not None, name
    return ref


def _buttons(nodes: list[UiNode] | tuple[UiNode, ...]) -> list[UiButton]:
    out: list[UiButton] = []
    for node in nodes:
        if isinstance(node, UiButton):
            out.append(node)
        elif isinstance(node, (UiTab, UiParameterBlock)):
            out.extend(_buttons(node.children))
    return out


def test_finger_id_validation(ui: DynamicUI) -> None:
    finger = _ref(ui, "FINACT_Fa1FingerId")
    started = time.perf_counter()
    with pytest.raises(ParameterValidationError) as err:
        ui.write_parameter(finger, "200")
    elapsed = time.perf_counter() - started
    assert err.value.message == (
        "FingerId ist 200, aber der Fingerscanner kann nur 149 Finger verwalten."
    )
    assert ui.get_value(finger) == "0"
    ui.write_parameter(finger, "100")
    assert ui.get_value(finger) == "100"
    print(f"validation: {elapsed * 1000:.1f} ms")


def test_scanner_change_is_checked_against_finger_ids(ui: DynamicUI) -> None:
    scanner = _ref(ui, "ACC_FingerprintScanner")
    ui.write_parameter(scanner, "1")
    ui.write_parameter(_ref(ui, "FINACT_Fa1FingerId"), "180")
    with pytest.raises(ParameterValidationError) as err:
        ui.write_parameter(scanner, "0")
    assert err.value.message.startswith("Auf Finger-Seite gibt es FingerIds > 149.")


def test_logic_relative_absolute_calculation(ui: DynamicUI) -> None:
    abs_rel = "M-00FA_A-A601-AF-CB97_UP-1001377_R-100137701"
    abs_write = "M-00FA_A-A601-AF-CB97_UP-1001378_R-100137802"
    rel_write = "M-00FA_A-A601-AF-CB97_UP-1001459_R-100145901"
    ui.write_parameter(abs_rel, "1")
    started = time.perf_counter()
    changes = ui.write_parameter(abs_write, "150")
    elapsed = time.perf_counter() - started
    assert ui.get_value(rel_write) == "48"
    assert rel_write in changes
    print(f"calculation: {elapsed * 1000:.1f} ms")


def test_buttons_and_offline_sort(app: Application, ui: DynamicUI) -> None:
    buttons = {b.handler: b for b in _buttons(ui.ui())}
    assert {"ACC_enrollFinger", "ACC_searchFingerId", "ACC_sort"} <= set(buttons)
    assert buttons["ACC_enrollFinger"].online == "ConnectionOriented"
    started = time.perf_counter()
    run_offline_button(ui, buttons["ACC_sort"])
    print(f"ACC_sort: {(time.perf_counter() - started) * 1000:.1f} ms")
