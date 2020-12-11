#!/usr/bin/python

# (c) 2020, Lucas Basquerotto
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# pylint: disable=missing-module-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=wrong-import-position
# pylint: disable=import-error

from __future__ import absolute_import, division, print_function

from ansible_collections.lrd.cloud.plugins.module_utils.lrd_util_schema import validate
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
    type: dict
    required: true
  validate_schema:
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
    validate_schema: false

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
          value=dict(type='dict', required=True),
          validate_schema=dict(type='bool', default=True),
      )
  )

  schema_file = module.params['schema_file']
  value = module.params['value']
  validate_schema = module.boolean(module.params['validate_schema'])

  schema = load_yaml_file(schema_file)
  error_msgs = validate(schema, value, validate_schema)

  if error_msgs:
    context = "schema validation"
    module.fail_json(msg=to_text(error_text(error_msgs, context)))

  module.exit_json(changed=False)


if __name__ == '__main__':
  main()
