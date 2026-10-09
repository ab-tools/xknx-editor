from __future__ import annotations

import io
import zipfile

from xknxeditor.prod import Archive
from xknxeditor.prod.baggage import Baggages

_INDEX = rb"""<?xml version="1.0" encoding="utf-8"?>
<KNX xmlns="http://knx.org/xml/project/20"><ManufacturerData><Manufacturer RefId="M-00FA">
<Baggages>
<Baggage TargetPath="A6\01" Name="Help_de.zip" Id="M-00FA_BG-Help" />
<Baggage TargetPath="A6\01" Name="Icons.zip" Id="M-00FA_BG-Icons" />
<Baggage TargetPath="" Name="missing.png" Id="M-00FA_BG-Missing" />
</Baggages></Manufacturer></ManufacturerData></KNX>"""


def _zip(files: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        for name, data in files.items():
            zf.writestr(name, data)
    return buffer.getvalue()


def _knxprod() -> bytes:
    return _zip(
        {
            "knx_master.xml": b"<KNX/>",
            "M-00FA/Catalog.xml": b"<KNX/>",
            "M-00FA/Hardware.xml": b"<KNX/>",
            "M-00FA/Baggages.xml": _INDEX,
            "M-00FA/Baggages/A6/01/Help_de.zip": _zip(
                {"ACC-Aktion.txt": "\ufeff### Aktion\r\n\r\nText".encode()}
            ),
            "M-00FA/Baggages/A6/01/Icons.zip": _zip({"alert.png": b"PNG"}),
        }
    )


def test_baggages_are_read_by_id() -> None:
    with Archive(_knxprod()) as archive:
        files = archive.get_baggages("M-00FA")
    assert set(files) == {"M-00FA_BG-Help", "M-00FA_BG-Icons"}


def test_help_and_icon_lookup() -> None:
    with Archive(_knxprod()) as archive:
        baggages = Baggages(archive.get_baggages("M-00FA"))
    assert (
        baggages.help_text("M-00FA_BG-Help", "ACC-Aktion") == "### Aktion\r\n\r\nText"
    )
    assert baggages.help_text("M-00FA_BG-Help", "acc-aktion") is not None
    assert baggages.help_text("M-00FA_BG-Help", "Missing") is None
    assert baggages.help_text(None, "ACC-Aktion") is None
    assert baggages.icon("M-00FA_BG-Icons", "alert") == b"PNG"
