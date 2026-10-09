"""Parameter changes with calculations: persistence, undo and the per-path modes."""

from __future__ import annotations

from pathlib import Path

import pytest

from editor_gui.plugins.base import Logger
from editor_gui.plugins.catalog.service import CatalogService
from editor_gui.plugins.logger.service import LogService
from editor_gui.plugins.project.service import ProjectService, _history_label
from xknxeditor.prod import Application
from xknxeditor.prod.application import parse_application_xml
from xknxeditor.prod.script import CalculationError, ParameterValidationError

APP = "M-00FA_A-0001-01-0000"


def _ref(n: int) -> str:
    return f"{APP}_P-{n}_R-{n}"


def _fixture() -> Path:
    for parent in Path(__file__).resolve().parents:
        cand = (
            parent
            / "packages"
            / "prod"
            / "tests"
            / "fixtures"
            / "calculations_application.xml"
        )
        if cand.exists():
            return cand
    raise FileNotFoundError("calculations_application.xml not found")


@pytest.fixture
def app() -> Application:
    return parse_application_xml(_fixture().read_bytes(), "M-00FA")[0]


@pytest.fixture
def proj(tmp_path: Path) -> ProjectService:
    service = ProjectService(CatalogService(tmp_path / "c.xknxcatalog"))
    service.set_logger(Logger(LogService(), "project"))
    service.new(tmp_path / "p.xknx")
    return service


def _add(proj: ProjectService, app: Application) -> int:
    node_id = proj.add_device("P-1", "HP-1", "Calc", app)
    assert node_id is not None
    return node_id


def _stored(proj: ProjectService, node_id: int) -> dict[str, str]:
    proj._refresh_device(node_id)
    device = proj.find_device_by_node_id(node_id)
    assert device is not None
    return {p.ref_id: p.value for p in device.parameter_instance_refs}


def test_edit_persists_calculated_values_as_one_step(
    proj: ProjectService, app: Application
) -> None:
    node_id = _add(proj, app)
    device = proj.find_device_by_node_id(node_id)
    assert device is not None
    proj.set_param(device, _ref(1), "5")
    stored = _stored(proj, node_id)
    assert stored[_ref(1)] == "5"
    assert stored[_ref(2)] == "11"
    assert stored[_ref(4)] == "15"

    assert proj.undo()
    stored = _stored(proj, node_id)
    assert _ref(1) not in stored
    assert _ref(2) not in stored
    device = proj.find_device_by_node_id(node_id)
    assert device is not None
    assert device.get_param_value(_ref(2)) == "2"


def test_rejected_edit_stores_nothing(proj: ProjectService, app: Application) -> None:
    node_id = _add(proj, app)
    device = proj.find_device_by_node_id(node_id)
    assert device is not None
    with pytest.raises(CalculationError):
        proj.set_param(device, _ref(5), "9")
    assert proj.param_error(node_id, _ref(5)) == (
        "Scripting engine returned with error 'bad'."
    )
    assert _ref(5) not in _stored(proj, node_id)
    device = proj.find_device_by_node_id(node_id)
    assert device is not None
    with pytest.raises(ValueError):
        proj.set_param(device, _ref(1), "5000")
    assert proj.param_error(node_id, _ref(1)) is not None
    proj.set_param(device, _ref(1), "2")
    assert proj.param_error(node_id, _ref(1)) is None


def test_transfer_runs_calculations_and_skips_rejected(
    proj: ProjectService, app: Application
) -> None:
    node_id = _add(proj, app)
    assert proj._apply_params(node_id, [(_ref(5), "9"), (_ref(3), "20")]) == 1
    stored = _stored(proj, node_id)
    assert stored[_ref(3)] == "20"
    assert stored[_ref(4)] == "21"
    assert _ref(5) not in stored


def test_raw_mode_skips_calculations(proj: ProjectService, app: Application) -> None:
    node_id = _add(proj, app)
    device = proj.find_device_by_node_id(node_id)
    assert device is not None
    proj.edit_params(device, [(_ref(1), "7")], mode="raw")
    stored = _stored(proj, node_id)
    assert stored[_ref(1)] == "7"
    assert _ref(2) not in stored


def test_recalculate_persists_derived_values(
    proj: ProjectService, app: Application
) -> None:
    node_id = _add(proj, app)
    device = proj.find_device_by_node_id(node_id)
    assert device is not None
    proj.edit_params(device, [(_ref(1), "7")], mode="raw")
    proj.recalculate_params(node_id, [_ref(1)])
    assert _stored(proj, node_id)[_ref(2)] == "15"


def test_labelled_composite_history() -> None:
    assert _history_label(
        "Composite", {"events": [], "label": "Button X executed."}
    ) == ("Button X executed.")


def test_validation_rejects_edit_but_not_transfer(
    proj: ProjectService, app: Application
) -> None:
    node_id = _add(proj, app)
    device = proj.find_device_by_node_id(node_id)
    assert device is not None
    with pytest.raises(ParameterValidationError):
        proj.set_param(device, _ref(3), "13")
    assert device.param_errors[_ref(3)] == (
        "Parameter value cannot be set, because validation failed."
    )
    assert _ref(3) not in _stored(proj, node_id)
    assert proj._apply_params(node_id, [(_ref(3), "13")]) == 1
    assert _stored(proj, node_id)[_ref(3)] == "13"
