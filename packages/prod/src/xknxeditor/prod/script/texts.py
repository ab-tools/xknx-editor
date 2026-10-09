"""Error texts the script host reports to scripts and users.

Texts not marked as observed are best guesses kept in one place so
they can be corrected once observed. .NET Framework messages follow the user's language."""

from __future__ import annotations

from .errors import COR_E_EXCEPTION

# Observed: online calls without a connection, and CoAP on a device without IoT support.
NOT_CONNECTED = "Not connected"
COAP_NOT_SUPPORTED = "CoAP Operations can only be performed for IoT Devices."
CANCELED = "The operation was canceled."

# Observed: value checks when a script or a calculation sets a parameter.
VALUE_OUT_OF_RANGE = (
    "The maximum length cannot exceed (valid range: {0}-{1}, but was {2})"
)
TEXT_TOO_LONG = "The maximum byte length cannot exceed."
ENUM_VALUE_NOT_FOUND = "The given value cannot be found."
VALUE_ERROR_NUMBER = COR_E_EXCEPTION

# Observed: number of System.FormatException.
COR_E_FORMAT = -2146233033

_DOTNET: dict[str, dict[str, str]] = {
    "key_not_found": {
        "en": "The given key was not present in the dictionary.",
        "de": "Der angegebene Schlüssel war nicht im Wörterbuch angegeben.",
        "nl": "De opgegeven sleutel is niet aanwezig in de woordenlijst.",
    },
    "null_reference": {
        "en": "Object reference not set to an instance of an object.",
        "de": "Der Objektverweis wurde nicht auf eine Objektinstanz festgelegt.",
        "nl": "De objectverwijzing is niet op een exemplaar van een object ingesteld.",
    },
    "invalid_cast": {
        "en": "Unable to cast object of type '{0}' to type '{1}'.",
        "de": 'Das Objekt des Typs "{0}" kann nicht in Typ "{1}" umgewandelt werden.',
        "nl": "Kan object van het type {0} niet converteren naar het type {1}.",
    },
    # Observed; the first English line of "property_empty" is reworded.
    "resource_not_available": {
        "en": "The selected device resource is currently not available.",
        "de": "Die ausgewählte Geräte-Ressource ist zurzeit nicht verfügbar.",
    },
    "property_empty": {
        "en": "An attempt was made to read a protected or nonexistent memory area.\n"
        "Failed to read Property({0}/{1}, {2}, {3}): Empty response",
        "de": "Es wurde versucht, einen geschützten oder nicht vorhandenen Speicherbereich "
        "zu lesen.\nLesen von Property({0}/{1}, {2}, {3}) fehlgeschlagen: Empty response",
    },
    "format": {
        "en": "Input string was not in a correct format.",
        "de": "Die Eingabezeichenfolge hat das falsche Format.",
        "nl": "De indeling van de invoertekenreeks is onjuist.",
    },
}


def dotnet_text(key: str, locale: str | None) -> str:
    """A .NET Framework exception message in the language of ``locale`` (BCP 47)."""
    from .compat.runtime import system_locale

    texts = _DOTNET[key]
    language = (locale or system_locale()).split("-")[0].lower()
    return texts.get(language, texts["en"])
