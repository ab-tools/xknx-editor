from __future__ import annotations

from pathlib import Path

from xknxeditor.prod.application import parse_application_xml
from xknxeditor.prod.parser_v2.dynamic import DynamicUI
from xknxeditor.prod.parser_v2.ui import UiButton, UiNode, UiParameterBlock, UiTab

APP = "M-00FA_A-0001-01-0000"
XML = (
    Path(__file__).parents[2] / "fixtures" / "calculations_application.xml"
).read_bytes()


def _buttons(nodes: list[UiNode] | tuple[UiNode, ...]) -> list[UiButton]:
    out: list[UiButton] = []
    for node in nodes:
        if isinstance(node, UiButton):
            out.append(node)
        elif isinstance(node, (UiTab, UiParameterBlock)):
            out.extend(_buttons(node.children))
    return out


def test_buttons_are_evaluated() -> None:
    ui = DynamicUI(parse_application_xml(XML, "M-00FA")[0].program)
    buttons = {b.id: b for b in _buttons(ui.ui())}

    run = buttons[f"{APP}_B-1"]
    assert (run.text, run.handler, run.handler_parameters) == (
        "Run",
        "offlineButton",
        '{"n": 2}',
    )
    assert run.online is None and run.module_instance_id is None
    assert buttons[f"{APP}_B-2"].online == "ConnectionOriented"
    assert f"{APP}_B-3" not in buttons
    label = buttons[f"{APP}_B-4"]
    assert label.read_only
    assert label.text == "Label n=1"

    mod = buttons[f"{APP}_MD-1_M-2_MI-1_B-1"]
    assert mod.text == "Channel 2"
    assert mod.handler_parameters == '{"ch": 2}'
    assert mod.module_instance_id == f"{APP}_MD-1_M-2_MI-1"
