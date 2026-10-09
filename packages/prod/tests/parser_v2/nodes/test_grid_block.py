from xknxeditor.namespaces.intermediate.application_program_channel_t import (
    ComObjectParameterBlock,
)
from xknxeditor.namespaces.intermediate.com_object_parameter_block_t_columns import (
    ComObjectParameterBlockColumns,
)
from xknxeditor.namespaces.intermediate.com_object_parameter_block_t_columns_column import (
    ComObjectParameterBlockColumnsColumn,
)
from xknxeditor.namespaces.intermediate.com_object_parameter_block_t_rows import (
    ComObjectParameterBlockRows,
)
from xknxeditor.namespaces.intermediate.com_object_parameter_block_t_rows_row import (
    ComObjectParameterBlockRowsRow,
)
from xknxeditor.namespaces.intermediate.parameter_block_layout_t import (
    ParameterBlockLayout,
)
from xknxeditor.prod.parser_v2.nodes import EvalContext, GlobalState
from xknxeditor.prod.parser_v2.nodes.com_object_parameter_block import (
    ComObjectParameterBlockNode,
)
from xknxeditor.prod.parser_v2.ui.parameter_block import UiParameterBlock


def test_grid_metadata() -> None:
    elem = ComObjectParameterBlock(
        id="PB-1",
        layout=ParameterBlockLayout.GRID,
        cell="2,3",
        rows=ComObjectParameterBlockRows(
            row=[
                ComObjectParameterBlockRowsRow(id="R-1", name="Row1"),
                ComObjectParameterBlockRowsRow(
                    id="R-2", name="Row2", text="Second", collapse_if_empty=True
                ),
            ]
        ),
        columns=ComObjectParameterBlockColumns(
            column=[
                ComObjectParameterBlockColumnsColumn(
                    id="C-1", name="Col1", width="45%"
                ),
                ComObjectParameterBlockColumnsColumn(
                    id="C-2", name="Col2", text="Mo", width="8%"
                ),
            ]
        ),
    )
    (block,) = ComObjectParameterBlockNode(elem, []).eval(EvalContext(GlobalState()))
    assert isinstance(block, UiParameterBlock)
    assert block.row_labels == ("", "Second")
    assert block.column_headers == ("", "Mo")
    assert block.column_widths == ("45%", "8%")
    assert block.collapsed_rows == frozenset({2})
    assert block.cell == "2,3"
