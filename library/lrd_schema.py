#!/usr/bin/python

# (c) 2020, Lucas Basquerotto
# Sponsored by Four Kitchens http://fourkitchens.com.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}


DOCUMENTATION = '''
---
module: lrd_schema
short_description: Validate a value according to a specified schema.
description:
   - Adds or removes a user from a MySQL database.
version_added: "0.6"
options:
  schema:
    description:
      - schema object to validate the value
    type: dict
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
notes:
   - You can specify schema_for_schema to validate the schema, but it's not required.

author: "Lucas Basquerotto (@lucasbasquerotto)"
'''

EXAMPLES = """
# Example with a successful validation of the schema and value
- lrd_schema:
    schema:
			root: "schema_root"
			schemas:
				schema_root:
					type: dict
					props:
						prop1:
							required: true
							type: str
						prop2:
							schema: schema_child
				schema_child:
					type: list
					elem_type: str
    value:
			prop1: "value1"
			prop2: ["value", "another_value"]

# Example with an unsuccessful validation of the value
- lrd_schema:
    schema:
			root: "schema_root"
			schemas:
				schema_root:
					type: dict
					props:
						prop1:
							required: true
							type: str
						prop2:
							schema: schema_child
				schema_child:
					type: list
					elem_type: str
    value:
			prop2: ["value", "another_value"]

# Another example with an unsuccessful validation of the value
- lrd_schema:
    schema:
			root: "schema_root"
			schemas:
				schema_root:
					type: dict
					props:
						prop1:
							required: true
							type: str
						prop2:
							schema: schema_child
				schema_child:
					type: list
					elem_type: str
    value:
			prop1: "value1"
			prop2: "value2"

# Yet another example with an unsuccessful validation of the value
- lrd_schema:
    schema:
			root: "schema_root"
			schemas:
				schema_root:
					type: dict
					props:
						prop1:
							required: true
							type: str
						prop2:
							schema: schema_child
				schema_child:
					type: list
					elem_type: str
    value:
			prop1: "value1"
			prop3: ["value", "another_value"]

# Example with an unsuccessful validation of the schema
- lrd_schema:
    schema:
			root: "schema_root"
			schemas:
				schema_root:
					typo: dict
					props:
						prop1:
							required: true
							type: str
						prop2:
							schema: schema_child
				schema_child:
					type: list
					elem_type: str
    value:
			prop2: ["value", "another_value"]
"""

import re
import string
import traceback
import yaml

from ansible.module_utils.basic import AnsibleModule

SCHEMA_BASE="""
root: "schema_wrapper"
schemas:
  schema_wrapper:
    type: "dict"
    props:
      root:
        required: true
        type: "string"
      schemas:
        required: true
        type: "map"
        elem_schema: "schema"
  schema:
    type: "dict"
    props:
      type:
        required: true
        type: "string"
      elem_type:
        type: "string"
      elem_schema:
        type: "string"
      non_empty:
        type: "bool"
      props:
        type: "map"
        elem_schema: "prop"
      choices:
        type: "list"
        elem_type: "string"
  prop:
    type: "dict"
    props:
      type:
        type: "string"
      schema:
        type: "string"
      elem_type:
        type: "string"
      elem_schema:
        type: "string"
      required:
        type: "bool"
      non_empty:
        type: "bool"
      values:
        type: "list"
        elem_type: "string"

"""

def validate_value(schema, value):
	schema_name=schema.root
	schema_dict=schema.schemas
	schema_ctx=''


# ===========================================
# Module execution.
#

def main():
    module = AnsibleModule(
        argument_spec=dict(
            schema=dict(type='dict', required=True),
            value=dict(type='dict', required=True),
            validate_schema=dict(type='bool', default=True),
        )
    )
    schema = module.params['schema']
    value = module.params['value']
    validate_schema = module.boolean(module.params['validate_schema'])

		if validate_schema:
			schema_base=yaml.load(SCHEMA_BASE)
			error_msgs=validate_value(schema_base, schema)

			if error_msgs:
        module.fail_json(msg='Error when validating schema\n\n' + to_native(error_msgs))

		error_msgs=validate_value(schema, value)

		if error_msgs:
			module.fail_json(msg='Error when validating value\n\n' + to_native(error_msgs))

    module.exit_json(changed=False)


if __name__ == '__main__':
    main()