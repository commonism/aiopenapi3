from typing import Dict, List
import logging

from .plugin import Document, Init


class Reduced(Document, Init):
    log = logging.getLogger("aiopenapi3.extra.Reduced")

    def __init__(self, operations: Dict[str, List[str]]):
        self.operations = operations
        super().__init__()

    def parsed(self, ctx: "Document.Context") -> "Document.Context":
        paths = {}
        try:
            npi = {}
            for path, methods in self.operations.items():
                pi = ctx.document["paths"][path]
                if methods is not None:
                    npi["parameters"] = pi.get("parameters", [])
                    for m in methods:
                        npi[m] = pi[m]
                else:
                    npi = pi
                paths[path] = npi
            ctx.document["paths"] = paths
        except KeyError as e:
            self.log.exception(e)
            raise e
        return ctx

    def paths(self, ctx: "Init.Context") -> "Init.Context":
        ctx.paths = None
        return ctx

    def initialized(self, ctx: "Init.Context") -> "Init.Context":
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
