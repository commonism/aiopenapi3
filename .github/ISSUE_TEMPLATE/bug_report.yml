name: aiopenapi3 Bug report
description: Report a bug or unexpected behavior in aiopenapi3
labels: [bug, unconfirmed]

body:
  - type: markdown
    attributes:
      value:  Thank you for taking the time to report a problem.

  - type: textarea
    id: description
    attributes:
      label: Description of the problem
      description: |
        Provide the detail required to understand the problem.
        Intention, Environment, Expectations, Failure
    validations:
      required: true

  - type: textarea
    id: example
    attributes:
      label: Example - Description Document/Code
      description: >
        [MRE](https://stackoverflow.com/help/minimal-reproducible-example) demonstrating the bug.
        Description Document (and Code).
      placeholder: |
        ...
      render: yaml

  - type: textarea
    id: version
    attributes:
      label: Python, Pydantic & OS Version
      description: |
        Which version of Python & Pydantic are you using, and which Operating System?

        Please run the following command and copy the output below:

        ```bash
        python3 -c "import pydantic.version; print(pydantic.version.version_info()); import aiopenapi3; print(aiopenapi3.__version__)"
        ```
      render: Text
    validations:
      required: true
