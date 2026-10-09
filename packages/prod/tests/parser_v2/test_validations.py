"""ParameterValidation on edits."""

from __future__ import annotations

from pathlib import Path

import pytest

from xknxeditor.prod.application import parse_application_xml
from xknxeditor.prod.parser_v2.calculation import VALIDATION_FAILED
from xknxeditor.prod.parser_v2.dynamic import DynamicUI
from xknxeditor.prod.script import ParameterValidationError

APP = "M-00FA_A-0001-01-0000"
MI = f"{APP}_MD-1_M-1_MI-1"
XML = (
    Path(__file__).parents[1] / "fixtures" / "calculations_application.xml"
).read_bytes()


def _ref(n: int) -> str:
    return f"{APP}_P-{n}_R-{n}"


@pytest.fixture
def ui() -> DynamicUI:
    dui = DynamicUI(parse_application_xml(XML, "M-00FA")[0].program)
    dui.ui()
    return dui


def test_returned_string_is_the_message(ui: DynamicUI) -> None:
    with pytest.raises(ParameterValidationError) as err:
        ui.edit_parameter(_ref(1), "600")
    assert err.value.message == "a too big: 600"
    assert err.value.ref_id == _ref(1)
    assert ui.get_value(_ref(1)) == "1"
    assert ui.get_value(_ref(2)) == "2"


def test_proposed_value_replaces_the_changed_input(ui: DynamicUI) -> None:
    ui.edit_parameter(_ref(1), "100")
    with pytest.raises(ParameterValidationError) as err:
        ui.edit_parameter(_ref(2), "450")
    assert err.value.message == "b too big: 450"


def test_non_true_result_gives_generic_message(ui: DynamicUI) -> None:
    with pytest.raises(ParameterValidationError) as err:
        ui.edit_parameter(_ref(3), "13")
    assert err.value.message == VALIDATION_FAILED
    assert ui.get_value(_ref(3)) == "3"
    ui.edit_parameter(_ref(3), "12")
    assert ui.get_value(_ref(3)) == "12"


def test_validation_can_be_skipped(ui: DynamicUI) -> None:
    ui.edit_parameter(_ref(3), "13", validate=False)
    assert ui.get_value(_ref(3)) == "13"


def test_calculation_outputs_are_not_validated(ui: DynamicUI) -> None:
    ui.edit_parameter(_ref(2), "21")
    ui.edit_parameter(_ref(1), "200")
    assert ui.get_value(_ref(2)) == "401"


def test_module_validation(ui: DynamicUI) -> None:
    with pytest.raises(ParameterValidationError) as err:
        ui.edit_parameter(f"{MI}_P-1_R-1", "60")
    assert err.value.message == "x must be below 50"
    assert err.value.ref_id == f"{MI}_P-1_R-1"
    ui.edit_parameter(f"{MI}_P-1_R-1", "40")
    assert ui.get_value(f"{MI}_P-2_R-2") == "140"


def test_type_error_uses_validation_error_ref(ui: DynamicUI) -> None:
    with pytest.raises(ParameterValidationError) as err:
        ui.edit_parameter(_ref(7), "X1")
    assert err.value.message == "Code must look like K123."
    ui.edit_parameter(_ref(7), "K12")
    assert ui.get_value(_ref(7)) == "K12"
