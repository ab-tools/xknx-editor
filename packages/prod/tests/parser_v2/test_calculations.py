"""ParameterCalculation plans and the DynamicUI change API."""

from __future__ import annotations

import pytest

from xknxeditor.prod.application import parse_application_xml
from xknxeditor.prod.parser_v2.dynamic import DynamicTreeBuilder, DynamicUI
from xknxeditor.prod.script import CalculationError

APP = "M-00FA_A-0001-01-0000"

SCRIPT = """
function double(input, output, context) { output.b = input.a * 2 + context.offset; }
function half(input, output) { output.a = Math.floor(input.b / 2); }
function accumulate(input, output) { output.c = output.c + input.b; }
function next(input, output) { output.d = input.c + 1; }
function nothing(input, output) {}
function boom(input, output) { throw new Error("bad"); }
function plus100(input, output) { output.y = input.x + 100; }
function label(input, output) { output.t = "n=" + input.a; }
"""


def _param(pid: str, name: str, value: str, pt: str = "N") -> str:
    return (
        f'<Parameter Id="{pid}" Name="{name}" ParameterType="{APP}_PT-{pt}" '
        f'Text="{name}" Value="{value}" />'
    )


def _calc(
    cid: str, lr: str, rl: str, left: list[str], right: list[str], params: str = ""
) -> str:
    lp = "".join(
        f'<ParameterRefRef RefId="{r}" AliasName="{a}" />'
        for r, a in (x.split("|") for x in left)
    )
    rp = "".join(
        f'<ParameterRefRef RefId="{r}" AliasName="{a}" />'
        for r, a in (x.split("|") for x in right)
    )
    extra = f' LRTransformationParameters="{params}"' if params else ""
    return (
        f'<ParameterCalculation Id="{cid}" Name="{cid[-4:]}" Language="JavaScript" LRTransformationFunc="{lr}" '
        f'RLTransformationFunc="{rl}"{extra}><LParameters>{lp}</LParameters>'
        f"<RParameters>{rp}</RParameters></ParameterCalculation>"
    )


def _ref(n: int) -> str:
    return f"{APP}_P-{n}_R-{n}"


MD = f"{APP}_MD-1"
MREF_X = f"{MD}_P-1_R-1"
MREF_Y = f"{MD}_P-2_R-2"

XML = f"""<?xml version="1.0" encoding="utf-8"?>
<KNX xmlns="http://knx.org/xml/project/20" CreatedBy="test" ToolVersion="1">
  <ManufacturerData>
    <Manufacturer RefId="M-00FA">
      <ApplicationPrograms>
        <ApplicationProgram Id="{APP}" ApplicationNumber="1" ApplicationVersion="1"
            ProgramType="ApplicationProgram" MaskVersion="MV-07B0" Name="Calc"
            LoadProcedureStyle="MergedProcedure" PeiType="0" DefaultLanguage="en-US"
            DynamicTableManagement="false" Linkable="false" MinEtsVersion="5.0">
          <Static>
            <ParameterTypes>
              <ParameterType Id="{APP}_PT-N" Name="N">
                <TypeNumber SizeInBit="16" Type="unsignedInt" minInclusive="0" maxInclusive="1000" />
              </ParameterType>
              <ParameterType Id="{APP}_PT-T" Name="T">
                <TypeText SizeInBit="160" />
              </ParameterType>
            </ParameterTypes>
            <Parameters>
              {_param(f"{APP}_P-1", "A", "1")}
              {_param(f"{APP}_P-2", "B", "2")}
              {_param(f"{APP}_P-3", "C", "3")}
              {_param(f"{APP}_P-4", "D", "4")}
              {_param(f"{APP}_P-5", "E", "5")}
              {_param(f"{APP}_P-6", "T", "n=1", "T")}
            </Parameters>
            <ParameterRefs>
              {"".join(f'<ParameterRef Id="{_ref(n)}" RefId="{APP}_P-{n}" />' for n in range(1, 7))}
            </ParameterRefs>
            <ParameterCalculations>
              {_calc(f"{APP}_PC-1", "double", "half", [f"{_ref(1)}|a"], [f"{_ref(2)}|b"], "{&quot;offset&quot;: 1}")}
              {_calc(f"{APP}_PC-2", "accumulate", "nothing", [f"{_ref(2)}|b"], [f"{_ref(3)}|c"])}
              {_calc(f"{APP}_PC-3", "next", "nothing", [f"{_ref(3)}|c"], [f"{_ref(4)}|d"])}
              {_calc(f"{APP}_PC-4", "boom", "nothing", [f"{_ref(5)}|e"], [f"{_ref(1)}|a"])}
              {_calc(f"{APP}_PC-5", "label", "nothing", [f"{_ref(1)}|a"], [f"{_ref(6)}|t"])}
            </ParameterCalculations>
            <Script>{SCRIPT}</Script>
          </Static>
          <ModuleDefs>
            <ModuleDef Id="{MD}" Name="Mod">
              <Static>
                <Parameters>
                  {_param(f"{MD}_P-1", "X", "0")}
                  {_param(f"{MD}_P-2", "Y", "0")}
                </Parameters>
                <ParameterRefs>
                  <ParameterRef Id="{MREF_X}" RefId="{MD}_P-1" />
                  <ParameterRef Id="{MREF_Y}" RefId="{MD}_P-2" />
                </ParameterRefs>
                <ParameterCalculations>
                  {_calc(f"{MD}_PC-1", "plus100", "nothing", [f"{MREF_X}|x"], [f"{MREF_Y}|y"])}
                </ParameterCalculations>
              </Static>
              <Dynamic>
                <ParameterBlock Id="{MD}_PB-1" Text="Mod">
                  <ParameterRefRef RefId="{MREF_X}" />
                  <ParameterRefRef RefId="{MREF_Y}" />
                </ParameterBlock>
              </Dynamic>
            </ModuleDef>
          </ModuleDefs>
          <Dynamic>
            <ChannelIndependentBlock>
              <ParameterBlock Id="{APP}_PB-1" Text="Main">
                {"".join(f'<ParameterRefRef RefId="{_ref(n)}" />' for n in range(1, 7))}
              </ParameterBlock>
              <Module Id="{MD}_M-1" RefId="{MD}" Text="M1" />
              <Module Id="{MD}_M-2" RefId="{MD}" Text="M2" />
            </ChannelIndependentBlock>
          </Dynamic>
        </ApplicationProgram>
      </ApplicationPrograms>
    </Manufacturer>
  </ManufacturerData>
</KNX>
"""


@pytest.fixture(scope="module")
def builder() -> DynamicTreeBuilder:
    app = parse_application_xml(XML.encode(), "M-00FA")[0]
    return DynamicTreeBuilder(app.program)


@pytest.fixture
def ui(builder: DynamicTreeBuilder) -> DynamicUI:
    app = parse_application_xml(XML.encode(), "M-00FA")[0]
    dui = DynamicUI(app.program, tree_builder=builder)
    dui.ui()
    return dui


def test_plan_is_topological_and_runs_each_calculation_once(
    builder: DynamicTreeBuilder,
) -> None:
    plan = [
        (c.id.rsplit("_", 1)[1], d) for c, d in builder.idx.calculation_plan(_ref(1))
    ]
    assert plan[0] == ("PC-1", "LR")
    assert plan.index(("PC-2", "LR")) < plan.index(("PC-3", "LR"))
    assert ("PC-4", "RL") in plan
    assert len(plan) == len(set(plan)) == 5


def test_lr_chain_with_context_and_output_prefill(ui: DynamicUI) -> None:
    changes = ui.edit_parameter(_ref(1), "5")
    assert ui.get_value(_ref(2)) == "11"
    assert ui.get_value(_ref(3)) == "14"
    assert ui.get_value(_ref(4)) == "15"
    assert ui.get_value(_ref(6)) == "n=5"
    assert changes == {
        _ref(1): ("1", "5"),
        _ref(2): ("2", "11"),
        _ref(3): ("3", "14"),
        _ref(4): ("4", "15"),
        _ref(6): ("n=1", "n=5"),
    }


def test_rl_direction_does_not_ping_pong(ui: DynamicUI) -> None:
    ui.edit_parameter(_ref(2), "21")
    assert ui.get_value(_ref(1)) == "10"
    assert ui.get_value(_ref(2)) == "21"
    assert ui.get_value(_ref(6)) == "n=10"


def test_unset_outputs_are_kept(ui: DynamicUI) -> None:
    assert ui.edit_parameter(_ref(3), "9") == {
        _ref(3): ("3", "9"),
        _ref(4): ("4", "10"),
    }
    assert ui.get_value(_ref(2)) == "2"


def test_script_error_rolls_back_the_edit(ui: DynamicUI) -> None:
    with pytest.raises(CalculationError) as err:
        ui.edit_parameter(_ref(5), "9")
    assert str(err.value) == "Scripting engine returned with error 'bad'."
    assert ui.get_value(_ref(5)) == "5"
    changes = ui.set_parameter_ref(_ref(5), "9")
    assert changes[_ref(5)] == ("5", "9")
    assert _ref(1) not in changes


def test_strict_type_check(ui: DynamicUI) -> None:
    with pytest.raises(ValueError):
        ui.edit_parameter(_ref(1), "5000")
    assert ui.get_value(_ref(1)) == "1"


def test_module_calculation_writes_qualified_ref(ui: DynamicUI) -> None:
    x1, y1 = f"{MD}_M-1_MI-1_P-1_R-1", f"{MD}_M-1_MI-1_P-2_R-2"
    y2 = f"{MD}_M-2_MI-1_P-2_R-2"
    assert ui.edit_parameter(x1, "3") == {x1: ("0", "3"), y1: ("0", "103")}
    assert ui.get_value(y1) == "103"
    assert ui.get_value(y2) == "0"


def test_apply_parameter_values_is_raw(ui: DynamicUI) -> None:
    ui.apply_parameter_values({_ref(1): "9"})
    assert ui.get_value(_ref(2)) == "2"
    ui.apply_parameter_values({_ref(1): None})
    assert ui.get_value(_ref(1)) == "1"


def test_active_parameter_ref_ids(ui: DynamicUI) -> None:
    active = ui.active_parameter_ref_ids()
    assert _ref(1) in active
    assert f"{MD}_M-2_MI-1_P-1_R-1" in active
