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

import datetime
import json
import re
import string
import sys
import yaml

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_text

try:
  from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
  from yaml import Loader, Dumper

def validate_next_value(schema_name, schema_ctx, value, schema_info_dict, error_msgs):
  schema_info=schema_info_dict.get(schema_name)

  if schema_info is None:
    error_msgs+=[
      'at: ' + (schema_ctx or '<root>'),
      'msg: schema <' + schema_name + '> is not defined'
    ]
    return error_msgs


  if schema_info.get('required') or schema_info.get('non_empty'):
    if value is None:
      error_msgs+=[
        'at: ' + (schema_ctx or '<root>'),
        'msg: value is not defined'
      ]
      return error_msgs

  if schema_info.get('non_empty'):
    if isinstance(value, list):
      if not len(value):
        error_msgs+=[
          'at: ' + (schema_ctx or '<root>'),
          'msg: list is empty'
        ]
        return error_msgs
    elif isinstance(value, collections.Mapping):
      if not len(value):
        error_msgs+=[
          'at: ' + (schema_ctx or '<root>'),
          'msg: dict is empty'
        ]
        return error_msgs
    else:
      if not str(value):
        error_msgs+=[
          'at: ' + (schema_ctx or '<root>'),
          'msg: value is empty'
        ]
        return error_msgs

  if value is not None:
    value_type=schema_info.get('type')

    if not value_type:
      error_msgs+=[
        'at: ' + (schema_ctx or '<root>'),
        'msg: type is not defined'
      ]
      return error_msgs

    allowed_types=[
      'unknown',
      'primitive',
      'string',
      'bool',
      'int',
      'float',
      'dict',
      'map',
      'list'
    ]

    if value_type not in allowed_types:
      error_msgs+=[
        'at: ' + (schema_ctx or '<root>'),
        'msg: type is invalid',
        'valid_types:',
        allowed_types
      ]
      return error_msgs

    if value_type in allowed_types:
      error_msgs+=[
        'at: ' + (schema_ctx or '<root>'),
        'msg: type is valid',
        'valid_types:',
        allowed_types
      ]
      return error_msgs

  error_msgs+=[
    'at: ' + schema_ctx,
    'msg: test'
  ]

  return error_msgs

def validate_value(schema, value):
  if schema is None:
    return ['main schema is not defined']

  schema_name=schema.get('root')
  schema_info_dict=schema.get('schemas')
  schema_ctx=''
  error_msgs=[]

  error_msgs=validate_next_value(schema_name, schema_ctx, value, schema_info_dict, error_msgs)

  return error_msgs

def output_text(output):
  return to_text(yaml.dump(output, Dumper=Dumper, default_flow_style=False))

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
      schema_base=yaml.load(SCHEMA_BASE, Loader=Loader)
      error_msgs=validate_value(schema_base, schema)

      if error_msgs:
        module.fail_json(msg='Error(s) when validating schema:\n\n' + output_text(error_msgs))

    error_msgs=validate_value(schema, value)

    if error_msgs:
      module.fail_json(msg='Error(s) when validating value:\n\n' + output_text(error_msgs))

    module.exit_json(changed=False)


if __name__ == '__main__':
    main()