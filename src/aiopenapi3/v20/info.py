from pydantic import Field

from ..base import ObjectExtended


class Contact(ObjectExtended):
    """
    Contact object belonging to an Info object, as described `here`_

    .. _here: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/2.0.md#contact-object
    """

    email: str = Field(default=None)
    name: str = Field(default=None)
    url: str = Field(default=None)


class License(ObjectExtended):
    """
    License object belonging to an Info object, as described `here`_

    .. _here: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/2.0.md#license-object
    """

    name: str = Field(...)
    url: str | None = Field(default=None)


class Info(ObjectExtended):
    """
    An OpenAPI Info object, as defined in `the spec`_.

    .. _here: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/2.0.md#info-object
    """

    title: str = Field(...)
    description: str | None = Field(default=None)
    termsOfService: str | None = Field(default=None)
    license: License | None = Field(default=None)
    contact: Contact | None = Field(default=None)
    version: str = Field(...)
