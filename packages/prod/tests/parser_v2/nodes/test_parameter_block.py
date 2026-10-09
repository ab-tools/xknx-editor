from xknxeditor.namespaces.intermediate.access_t import Access
from xknxeditor.namespaces.intermediate.application_program_channel_t import (
    ComObjectParameterBlock,
)
from xknxeditor.prod.parser_v2.nodes import EvalContext, GlobalState
from xknxeditor.prod.parser_v2.nodes.com_object_parameter_block import (
    ComObjectParameterBlockNode,
)
from xknxeditor.prod.parser_v2.ui.parameter_block import UiParameterBlock


def _eval(access: Access) -> list[object]:
    node = ComObjectParameterBlockNode(
        ComObjectParameterBlock(id="PB-1", text="Block", access=access), []
    )
    return list(node.eval(EvalContext(GlobalState())))


def test_read_access_marks_the_block_read_only() -> None:
    (block,) = _eval(Access.READ)
    assert isinstance(block, UiParameterBlock) and block.read_only
    (block,) = _eval(Access.READ_WRITE)
    assert isinstance(block, UiParameterBlock) and not block.read_only


def test_no_access_hides_the_block_but_keeps_it_evaluated() -> None:
    (block,) = _eval(Access.NONE)
    assert isinstance(block, UiParameterBlock) and block.hidden
    (block,) = _eval(Access.READ_WRITE)
    assert isinstance(block, UiParameterBlock) and not block.hidden
