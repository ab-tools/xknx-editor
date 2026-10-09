from __future__ import annotations

# HRESULTs that .NET exceptions carry when they cross into JScript.
E_FAIL = -2147467259
E_NOTIMPL = -2147467263
COR_E_ARGUMENT = -2147024809
COR_E_EXCEPTION = -2146233088
CLASS_NOT_AUTOMATION = -2146827858
COR_E_INVALIDOPERATION = -2146233079
COR_E_KEYNOTFOUND = -2146232969
COR_E_UNAUTHORIZEDACCESS = -2147024891


class ScriptError(Exception):
    """A script failed: compile error, uncaught exception or engine failure."""

    def __init__(
        self,
        message: str,
        *,
        name: str = "Error",
        number: int | None = None,
        line: int | None = None,
        column: int | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.name = name
        self.number = number
        self.line = line
        self.column = column


class ScriptCompileError(ScriptError):
    """The script text cannot be parsed."""


class ScriptAborted(ScriptError):
    """The run was force-stopped."""

    def __init__(self) -> None:
        super().__init__("Script aborted")


class HostError(Exception):
    """Raised by host functions; surfaces in the script as a catchable Error."""

    def __init__(self, message: str, *, number: int = E_FAIL) -> None:
        super().__init__(message)
        self.message = message
        self.number = number


class AbortRequested(Exception):
    """Raised by host functions to unwind a force-stopped script."""


class ParameterValidationError(ValueError):
    """A ParameterValidation (or type check) rejected a value."""

    def __init__(self, message: str, *, ref_id: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.ref_id = ref_id


class CalculationError(ValueError):
    """A ParameterCalculation failed; the triggering change is rejected."""

    def __init__(self, message: str, *, calculation_id: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.calculation_id = calculation_id
