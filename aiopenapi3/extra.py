from typing import List, Union, Optional, Tuple
import logging
import re

from .plugin import Document, Init


class Reduce(Document, Init):
    """
    The Reduce plugin removes all not listed PathItems from the paths, limits initialization to models required and removes non required schemas
    """

    log = logging.getLogger("aiopenapi3.extra.Reduce")

    def __init__(
        self,
        operations: List[
            Union[Tuple[Union[re.Pattern, str], Optional[List[Union[re.Pattern, str]]]], Union[re.Pattern, str]]
        ],
    ) -> None:
        self.operations = operations
        super().__init__()

    def _reduced_paths(self, ctx: "Document.Context") -> dict:
        reduced = {}
        keep_keys = {"summary", "description", "servers", "parameters"}
        for operation in self.operations:
            if isinstance(operation, (str, re.Pattern)):
                for path_key, path_value in ctx.document["paths"].items():
                    for operation_key, operation_value in path_value.items():
                        if "operationId" in operation_value and (
                            (isinstance(operation, str) and operation == operation_value["operationId"])
                            or (
                                isinstance(operation, re.Pattern)
                                and re.match(operation, operation_value["operationId"])
                            )
                        ):
                            if path_key not in reduced:
                                reduced[path_key] = {k: v for k, v in path_value.items() if k in keep_keys}
                            reduced[path_key][operation_key] = operation_value
            else:
                pattern, operation_patterns = operation
                for path_key in ctx.document["paths"].keys():
                    if (isinstance(pattern, str) and pattern == path_key) or (
                        isinstance(pattern, re.Pattern) and re.match(pattern, path_key)
                    ):
                        reduced[path_key] = {
                            k: v
                            for k, v in ctx.document["paths"][path_key].items()
                            if k in keep_keys
                            or not operation_patterns
                            or any(
                                (isinstance(op_pattern, str) and op_pattern == k)
                                or (isinstance(op_pattern, re.Pattern) and re.match(op_pattern, k))
                                for op_pattern in operation_patterns
                            )
                        }
        return reduced

    def parsed(self, ctx: "Document.Context") -> "Document.Context":
        """Parse the given context."""
        ctx.document["paths"] = self._reduced_paths(ctx)
        return ctx

    def paths(self, ctx: "Init.Context") -> "Init.Context":
        """Clear the paths of the context."""
        ctx.paths = None
        return ctx

    def initialized(self, ctx: "Init.Context") -> "Init.Context":
        """Process the initialized context."""
        for name, parameter in list(ctx.initialized.components.parameters.items()):
            if parameter.schema_._model_type is None:
                del ctx.initialized.components.parameters[name]
                break

        for name, schema in list(ctx.initialized.components.schemas.items()):
            if schema._model_type is None:
                del ctx.initialized.components.schemas[name]
                break

        for name, response in list(ctx.initialized.components.responses.items()):
            for k, v in response.content.items():
                if v.schema_._model_type is None:
                    del ctx.initialized.components.responses[name]
                    break

        for name, requestBody in list(ctx.initialized.components.requestBodies.items()):
            for k, v in requestBody.content.items():
                if v.schema_._model_type is None:
                    del ctx.initialized.components.requestBodies[name]
                    break
        return ctx


class Cull(Reduce):
    """The Cull plugin removes everything not required as early as possible"""

    @staticmethod
    def _extract_references(data, root=None):
        """
        Extracts references from the data using a generator.

        :param data: The data from which references are to be extracted.
        :param root: The root of the data. If not provided, data is used as root.
        """
        stack = [(data, root or data)]
        while stack:
            data, root = stack.pop()
            if isinstance(data, dict):
                for key, value in data.items():
                    # Check for reference keys in the data
                    if key == "$ref" or (isinstance(value, str) and value.startswith("#/")):
                        yield value
                    else:
                        stack.append((value, root))
            elif isinstance(data, list):
                for item in data:
                    stack.append((item, root))

    @classmethod
    def _update_references(cls, source, destination, target=None):
        """
        Updates references in the destination based on the source.

        :param source: The source data.
        :param destination: The destination where updates are to be made.
        :param target: The target references. If not provided, destination is used.
        :return: Boolean indicating if changes were made.
        """
        has_changes = False
        for ref in cls._extract_references(target or destination):
            if ref.startswith("#"):
                keys = ref[2:].split("/")
                source_cursor = source
                destination_cursor = destination
                for key in keys[:-1]:
                    if key not in destination_cursor:
                        destination_cursor[key] = {}
                    destination_cursor = destination_cursor[key]
                    source_cursor = source_cursor.get(key, {})
                last_key = keys[-1]
                if last_key not in destination_cursor:
                    has_changes = True
                    destination_cursor[last_key] = source_cursor.get(last_key, {})
        return has_changes

    def parsed(self, ctx: "Document.Context") -> "Document.Context":
        """
        Process the parsed document context.

        :param ctx: The document context to be processed.
        :return: The processed document context.
        """
        # Exclude certain keys from the document
        document = {k: v for k, v in ctx.document.items() if k not in ["components", "paths", "tags"]}
        # Restore security schemes
        document["components"] = {"securitySchemes": ctx.document.get("components", {}).get("securitySchemes", {})}
        # Process paths in the document
        document["paths"] = self._reduced_paths(ctx)
        # Update references in the document
        while self._update_references(ctx.document, document):
            pass
        # Rebuild Tags
        tag_names = list(
            set(
                tag
                for operations in document.get("paths", {}).values()
                for details in operations.values()
                if isinstance(details, dict)
                for tag in details.get("tags", [])
            )
        )
        document["tags"] = [tag for tag in ctx.document.get("tags", []) if tag["name"] in tag_names]

        ctx.document = document

        return ctx
