"""Copy/paste of a device configuration (parameters + group-address links) between identical
devices, plus duplicate carrying links, and the same-application guard."""

from __future__ import annotations

from pathlib import Path

from editor_gui.plugins.base import Logger
from editor_gui.plugins.catalog.service import CatalogService
from editor_gui.plugins.logger.service import LogService
from editor_gui.plugins.project.service import DeviceConfigClipboard, ProjectService

_APP_ID = "M-0008_A-7072-21-5CC3-O000A"


def _fixture() -> Path:
    p = Path(__file__).resolve()
    for parent in p.parents:
        cand = (
            parent
            / "packages"
            / "prod"
            / "tests"
            / "fixtures"
            / "gira_2gang_button_interface.knxprod"
        )
        if cand.exists():
            return cand
    raise FileNotFoundError("gira_2gang_button_interface.knxprod not found")


def _project(tmp_path: Path) -> tuple[ProjectService, CatalogService]:
    cat = CatalogService(tmp_path / "c.xknxcatalog")
    cat.import_knxprod(_fixture())
    proj = ProjectService(cat)
    proj.set_logger(Logger(LogService(), "project"))
    proj.new(tmp_path / "p.xknx")
    return proj, cat


def _add(proj: ProjectService, cat: CatalogService, name: str) -> int:
    product = next(p for p in cat.get_products() if p.application_id == _APP_ID)
    app = cat.get_application(_APP_ID)
    assert app is not None
    dev_id = proj.add_device(
        product.product_ref_id, product.hardware2program_ref_id, name, app
    )
    assert dev_id is not None
    return dev_id


def _com_object(proj: ProjectService, node_id: int, suffix: str):
    device = proj.find_device_by_node_id(node_id)
    assert device is not None
    return next(co for co in device.get_visible_com_objects() if co.id.endswith(suffix))


def test_paste_links_onto_identical_device(tmp_path: Path) -> None:
    proj, cat = _project(tmp_path)
    src = _add(proj, cat, "Source")
    dst = _add(proj, cat, "Target")

    co = _com_object(proj, src, "_M-200_MI-1_O-2-0_R-1")
    assert co.db_id is not None
    ga_id = proj.create_group_address_value(0x0B00, "chan")
    assert ga_id is not None
    assert proj.link_com_object_to_ga(co.db_id, ga_id, is_sending=True) is not None

    clip = proj.copy_device_config(src)
    assert clip is not None
    assert clip.links  # the source link was captured

    ok, params, links = proj.paste_device_config(
        dst, clip, include_params=False, include_links=True
    )
    assert ok
    assert params == 0
    assert links >= 1

    dco = _com_object(proj, dst, "_M-200_MI-1_O-2-0_R-1")
    assert dco.db_id is not None
    assignments = proj.get_links_for_com_object(dco.db_id)
    assert [(a.group_address_id, a.is_sending) for a in assignments] == [(ga_id, True)]


def test_paste_params_reinstantiates_com_objects(tmp_path: Path) -> None:
    proj, cat = _project(tmp_path)
    app = cat.get_application(_APP_ID)
    assert app is not None
    prog = app.program.id

    # Source carries a non-default M-100 function that re-instantiates that channel's object.
    product = next(p for p in cat.get_products() if p.application_id == _APP_ID)
    src = proj.add_device(
        product.product_ref_id,
        product.hardware2program_ref_id,
        "Source",
        app,
        parameters=[(f"{prog}_MD-1_M-100_MI-1_P-149_R-142", "5")],
    )
    assert src is not None
    dst = _add(proj, cat, "Target")

    clip = proj.copy_device_config(src)
    assert clip is not None
    ok, params, _ = proj.paste_device_config(
        dst, clip, include_params=True, include_links=False
    )
    assert ok
    assert params >= 1

    target = proj.find_device_by_node_id(dst)
    assert target is not None
    ids = {co.id for co in target.get_visible_com_objects()}
    assert f"{prog}_MD-1_M-100_MI-1_O-2-0_R-173" in ids


def test_duplicate_with_links_carries_links(tmp_path: Path) -> None:
    proj, cat = _project(tmp_path)
    src = _add(proj, cat, "Source")

    co = _com_object(proj, src, "_M-200_MI-1_O-2-0_R-1")
    assert co.db_id is not None
    ga_id = proj.create_group_address_value(0x0B01, "chan")
    assert ga_id is not None
    assert proj.link_com_object_to_ga(co.db_id, ga_id, is_sending=True) is not None

    (clone_id,) = proj.clone_device(src, 1, include_params=True, include_links=True)
    cco = _com_object(proj, clone_id, "_M-200_MI-1_O-2-0_R-1")
    assert cco.db_id is not None
    assignments = proj.get_links_for_com_object(cco.db_id)
    assert [(a.group_address_id, a.is_sending) for a in assignments] == [(ga_id, True)]


def test_duplicate_without_links_has_none(tmp_path: Path) -> None:
    proj, cat = _project(tmp_path)
    src = _add(proj, cat, "Source")
    co = _com_object(proj, src, "_M-200_MI-1_O-2-0_R-1")
    assert co.db_id is not None
    ga_id = proj.create_group_address_value(0x0B02, "chan")
    assert ga_id is not None
    proj.link_com_object_to_ga(co.db_id, ga_id, is_sending=True)

    (clone_id,) = proj.clone_device(src, 1)  # default: no links
    cco = _com_object(proj, clone_id, "_M-200_MI-1_O-2-0_R-1")
    assert cco.db_id is not None
    assert proj.get_links_for_com_object(cco.db_id) == []


def test_paste_rejects_different_application(tmp_path: Path) -> None:
    proj, cat = _project(tmp_path)
    dst = _add(proj, cat, "Target")
    foreign = DeviceConfigClipboard(
        app_id="M-FFFF_A-0000-00-0000-O0000",
        source_label="other",
        params=[],
        links=[],
    )
    ok, params, links = proj.paste_device_config(dst, foreign)
    assert (ok, params, links) == (False, 0, 0)


class _Api:
    """Minimal PluginAPI stand-in exposing only the project service the paste uses."""

    def __init__(self, project: ProjectService) -> None:
        self.project = project


def _paste_links_plugin(proj: ProjectService):
    """Bind the plugin's link-paste method to a bare instance (skips panel construction)."""
    from editor_gui.plugins.project.plugin import ProjectPlugin

    plugin = ProjectPlugin.__new__(ProjectPlugin)
    plugin._api = _Api(proj)  # type: ignore[attr-defined]
    return plugin._paste_com_object_links


def test_paste_com_object_links_replace(tmp_path: Path) -> None:
    proj, cat = _project(tmp_path)
    dst = _add(proj, cat, "Target")
    co = _com_object(proj, dst, "_M-200_MI-1_O-2-0_R-1")
    assert co.db_id is not None
    existing = proj.create_group_address_value(0x0B10, "old")
    assert existing is not None
    proj.link_com_object_to_ga(co.db_id, existing, is_sending=True)

    new_ga = proj.create_group_address_value(0x0B11, "new")
    assert new_ga is not None
    _paste_links_plugin(proj)(co.db_id, [(new_ga, True)], True)

    assignments = proj.get_links_for_com_object(co.db_id)
    assert [(a.group_address_id, a.is_sending) for a in assignments] == [(new_ga, True)]


def test_paste_com_object_links_merge_keeps_existing_and_skips_duplicates(
    tmp_path: Path,
) -> None:
    proj, cat = _project(tmp_path)
    dst = _add(proj, cat, "Target")
    co = _com_object(proj, dst, "_M-200_MI-1_O-2-0_R-1")
    assert co.db_id is not None
    existing = proj.create_group_address_value(0x0B20, "keep")
    assert existing is not None
    proj.link_com_object_to_ga(co.db_id, existing, is_sending=True)

    extra = proj.create_group_address_value(0x0B21, "extra")
    assert extra is not None
    # Merge: the duplicate (existing) is skipped, the extra is added receive-only because the
    # target already has a sending link.
    _paste_links_plugin(proj)(co.db_id, [(existing, True), (extra, True)], False)

    assignments = proj.get_links_for_com_object(co.db_id)
    result = sorted((a.group_address_id, a.is_sending) for a in assignments)
    assert result == sorted([(existing, True), (extra, False)])
