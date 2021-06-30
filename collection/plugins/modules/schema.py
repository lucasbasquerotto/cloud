#!/usr/bin/python

# (c) 2020, Lucas Basquerotto
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# pylint: disable=missing-module-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=wrong-import-position
# pylint: disable=import-error
# pylint: disable=broad-except

# pyright: reportUnusedImport=true
# pyright: reportUnusedVariable=true
# pyright: reportMissingImports=false

from __future__ import absolute_import, division, print_function

import os
import traceback

from ansible_collections.lrd.cloud.plugins.module_utils.lrd_util_schema import validate_schema
from ansible_collections.lrd.cloud.plugins.module_utils.lrd_utils import error_text, load_yaml_file

from ansible.module_utils._text import to_text
from ansible.module_utils.basic import AnsibleModule

__metaclass__ = type  # pylint: disable=invalid-name

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}


DOCUMENTATION = '''
---
module: lrd.cloud.schema
short_description: Validate a value according to a specified schema.
description:
   - Validate a value according to a specified schema.
version_added: "2.8"
options:
  schema_file:
    description:
      - schema file to validate the value
    type: str
    required: true
  value:
    description:
      - value to be validated according to the schema
    type: raw
    required: true
  full_validation:
    description:
      - specifies if the schema itself must be validated
    type: bool
    default: true

author: "Lucas Basquerotto (@lucasbasquerotto)"
'''

EXAMPLES = """
# Schema File 1 (schemas/my_file_1.yml):

# root: "schema_root"
# schemas:
#   schema_root:
#     type: dict
#     props:
#       prop1:
#         required: true
#         type: str
#       prop2:
#         schema: schema_child
#   schema_child:
#     type: list
#     elem_type: str

# Example with a successful validation of the schema and value
- lrd_schema:
    schema_file: "schemas/my_file_1.yml"
    value:
      prop1: "value1"
      prop2: ["value", "another_value"]

# Example with an unsuccessful validation of the value
- lrd_schema:
    schema_file: "schemas/my_file_1.yml"
    value:
      prop2: ["value", "another_value"]

# Another example with an unsuccessful validation of the value
- lrd_schema:
    schema_file: "schemas/my_file_1.yml"
    value:
      prop1: "value1"
      prop2: "value2"

# Yet another example with an unsuccessful validation of the value
# and don't validate the schema
- lrd_schema:
    schema_file: "schemas/my_file_1.yml"
    value:
      prop1: "value1"
      prop3: ["value", "another_value"]
    full_validation: false

# Schema File 2 (schemas/my_file_2.yml):
# (invalid: 'typo' instead of 'type')

# root: "schema_root"
# schemas:
#   schema_root:
#     typo: dict
#     props:
#       prop1:
#         required: true
#         type: str
#       prop2:
#         schema: schema_child
#   schema_child:
#     type: list
#     elem_type: str

# Example with an unsuccessful validation of the schema
- lrd_schema:
    schema_file: "schemas/my_file_2.yml"
    value:
      prop2: ["value", "another_value"]
"""

# ===========================================
# Module execution.
#


def main():
  module = AnsibleModule(
      argument_spec=dict(
          schema_file=dict(type='str', required=True),
          value=dict(type='raw', required=True),
          full_validation=dict(type='bool', default=True),
      )
  )

  schema_file = module.params['schema_file']
  value = module.params['value']
  full_validation = module.boolean(module.params['full_validation'])

  error_msgs = list()

  if os.path.exists(schema_file):
    schema = None

    try:
      schema = load_yaml_file(schema_file)
    except Exception as error:
      error_msgs += [[
          str('file: ' + schema_file),
          'msg: error when trying to load the schema file',
          'error type: ' + str(type(error)),
          'error details: ',
          traceback.format_exc().split('\n'),
      ]]

    if schema:
      error_msgs_aux = validate_schema(schema, value, full_validation)

      for value in (error_msgs_aux or []):
        new_value = [str('schema file: ' + schema_file)] + value
        error_msgs += [new_value]
  else:
    error_msgs += [[str('schema file not found: ' + schema_file)]]

  if error_msgs:
    context = "schema validation"
    module.fail_json(msg=to_text(error_text(error_msgs, context)))

  module.exit_json(changed=False)


if __name__ == '__main__':
  main()
