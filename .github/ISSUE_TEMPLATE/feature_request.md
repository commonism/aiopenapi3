name: Feature request
description: Suggest a new feature for aiopenapi3
labels: [feature]

body:
  - type: markdown
    attributes:
      value: Thank you for proposing an improvement ✊

  - type: checkboxes
    id: searched
    attributes:
      label: Initial Checks
      description: |
        It does not exist or is related to OpenAPI or other libraries can do it already
      options:
        - label: I have searched Google & GitHub for similar requests and couldn't find anything
          required: true
        - label: I have read [the docs](https://aiopenapi3.readthedocs.org) and still think this feature is missing
          required: true

  - type: textarea
    id: description
    attributes:
      label: Description
      description: |
        Please give as much detail as possible about the feature you would like to suggest. 🙏

        You might like to add:
        * A demo of how code might look when using the feature
        * Your use case(s) for the feature
    validations:
      required: true
