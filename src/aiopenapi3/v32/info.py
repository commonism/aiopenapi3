from pydantic import Field, EmailStr, model_validator

from aiopenapi3.base import ObjectExtended


class Contact(ObjectExtended):
    """
    4.3 Contact Object

    Contact information for the exposed API.

    As described `here`_

    .. _here: https://spec.openapis.org/oas/v3.2.0.html#contact-object
    """

    email: EmailStr = Field(default=None)
    name: str = Field(default=None)
    url: str = Field(default=None)


class License(ObjectExtended):
    """
    4.4 License Object

    License information for the exposed API.

    As described `here`_

    .. _here: https://spec.openapis.org/oas/v3.2.0.html#license-object
    """

    name: str = Field(...)
    identifier: str | None = Field(default=None)
    url: str | None = Field(default=None)

    @model_validator(mode="after")
    def validate_License(self):
        """
        A URL to the license used for the API. This MUST be in the form of a URL. The url field is mutually exclusive of the identifier field.
        """
        assert not all([getattr(self, i, None) is not None for i in ["identifier", "url"]])
        return self


class Info(ObjectExtended):
    """
    4.2 Info Object

    The object provides metadata about the API. The metadata MAY be used by the clients if needed,
    and MAY be presented in editing or documentation generation tools for convenience.

    As described `here`_
    .. _here: https://spec.openapis.org/oas/v3.2.0.html#info-object
    """

    title: str = Field(...)
    summary: str | None = Field(default=None)
    description: str | None = Field(default=None)
    termsOfService: str | None = Field(default=None)
    contact: Contact | None = Field(default=None)
    license: License | None = Field(default=None)
    version: str = Field(...)
