from typing import Dict, List, Union, Pattern
import logging
import re

from .plugin import Document, Init


class Reduced(Document, Init):
    log = logging.getLogger("aiopenapi3.extra.Reduced")

    def __init__(self, operations: Dict[Union[str, Pattern], List[str]]):
        """Initialize the Reduced object."""
        self.operations = operations
        super().__init__()

    def parsed(self, ctx: "Document.Context") -> "Document.Context":
        """Parse the given context."""
        paths = {}
        matched_paths = self._find_matched_paths(ctx)

        for path in matched_paths:
            paths[path] = self._extract_path_info(ctx, path)

        ctx.document["paths"] = paths
        return ctx

    def _find_matched_paths(self, ctx: "Document.Context") -> List[str]:
        """Find paths in the context that match the given operations."""
        return [
            path
            for path_pattern in self.operations.keys()
            for path in ctx.document["paths"].keys()
            if (isinstance(path_pattern, str) and path_pattern == path)
            or (isinstance(path_pattern, re.Pattern) and path_pattern.match(path))
        ]

    def _extract_path_info(self, ctx: "Document.Context", path: str) -> Dict:
        """Extract path information from the context based on the given path."""
        methods = self.operations[path]
        path_info = ctx.document["paths"][path]
        new_path_info = {}

        if methods is not None:
            new_path_info["parameters"] = path_info.get("parameters", [])
            for method in methods:
                new_path_info[method] = path_info[method]
        else:
            new_path_info = path_info

        return new_path_info

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
