from pydantic import Field, EmailStr, model_validator

from aiopenapi3.base import ObjectExtended


class Contact(ObjectExtended):
    """
    Contact object belonging to an Info object, as described `here`_

    .. _here: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.1.0.md#contactObject
    """

    email: EmailStr = Field(default=None)
    name: str = Field(default=None)
    url: str = Field(default=None)


class License(ObjectExtended):
    """
    License object belonging to an Info object, as described `here`_

    .. _here: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.1.0.md#license-object
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
    An OpenAPI Info object, as defined in `the spec`_.

    .. _here: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.1.0.md#info-object
    """

    title: str = Field(...)
    summary: str | None = Field(default=None)
    description: str | None = Field(default=None)
    termsOfService: str | None = Field(default=None)
    contact: Contact | None = Field(default=None)
    license: License | None = Field(default=None)
    version: str = Field(...)
