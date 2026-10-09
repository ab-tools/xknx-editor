from xknxeditor.namespaces.intermediate import ParameterSeparator
from xknxeditor.namespaces.intermediate.access_t import Access
from xknxeditor.namespaces.intermediate.parameter_separator_t_uihint import (
    ParameterSeparatorUihint,
)
from xknxeditor.namespaces.intermediate.text_alignment_t import TextAlignment
from xknxeditor.prod.parser_v2.nodes import EvalContext, GlobalState
from xknxeditor.prod.parser_v2.nodes.parameter_separator import ParameterSeparatorNode
from xknxeditor.prod.parser_v2.ui.separator import UiSeparator


def _eval(elem: ParameterSeparator) -> list[object]:
    return list(ParameterSeparatorNode(elem).eval(EvalContext(GlobalState())))


def test_hint_alignment_and_icon_are_kept() -> None:
    nodes = _eval(
        ParameterSeparator(
            id="S-1",
            text="Note",
            uihint=ParameterSeparatorUihint.INFORMATION,
            text_alignment=TextAlignment.CENTER,
            icon="info",
        )
    )
    assert nodes == [
        UiSeparator(
            id="S-1", text="Note", hint="Information", alignment="Center", icon="info"
        )
    ]


def test_ruler_without_text() -> None:
    nodes = _eval(
        ParameterSeparator(
            id="S-2", text="", uihint=ParameterSeparatorUihint.HORIZONTAL_RULER
        )
    )
    assert nodes == [UiSeparator(id="S-2", text=None, hint="HorizontalRuler")]


def test_access_none_hides_the_separator() -> None:
    assert _eval(ParameterSeparator(id="S-3", text="x", access=Access.NONE)) == []
