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
        type: "str"
      schemas:
        required: true
        type: "map"
        elem_schema: "schema"
  schema:
    type: "dict"
    props:
      type:
        required: true
        type: "str"
      elem_type:
        type: "str"
      elem_schema:
        type: "str"
      non_empty:
        type: "bool"
      props:
        type: "map"
        elem_schema: "prop"
      choices:
        type: "list"
        elem_type: "str"
  prop:
    type: "dict"
    props:
      type:
        type: "str"
      schema:
        type: "str"
      elem_type:
        type: "str"
      elem_schema:
        type: "str"
      required:
        type: "bool"
      non_empty:
        type: "bool"
      values:
        type: "list"
        elem_type: "str"

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

def by_value(item):
  return item[1]

def validate_next_value(schema_data, value, error_msgs):
  schema_name=schema_data.get('name')
  schema_ctx=schema_data.get('ctx')
  schema_info=schema_data.get('info')
  schema_info_dict=schema_data.get('dict')
  is_subelement=schema_data.get('subelement')
  required=schema_data.get('required')

  if schema_info is None:
    error_msgs+=[[
      'at: ' + (schema_ctx or '<root>'),
      'schema_name: ' + schema_name,
      'msg: schema is not defined'
    ]]
    return error_msgs

  if required or schema_info.get('non_empty'):
    if value is None:
      error_msgs+=[[
        'at: ' + (schema_ctx or '<root>'),
        'schema_name: ' + schema_name,
        'msg: value is not defined'
      ]]
      return error_msgs

  value_type=schema_info.get('type')
  next_schema=schema_info.get('schema')

  if (not is_subelement) and ('schema' in schema_info):
      error_msgs+=[[
        'at: ' + (schema_ctx or '<root>'),
        'schema_name: ' + schema_name,
        'msg: a schema definition shouldn\'t have a schema property'
      ]]
      return error_msgs
  elif (not value_type) and (not next_schema):
    error_msgs+=[[
      'at: ' + (schema_ctx or '<root>'),
      'schema_name: ' + schema_name,
      'msg: a definition should have either a type or schema property'
    ]]
    return error_msgs
  elif value_type and next_schema:
    error_msgs+=[[
      'at: ' + (schema_ctx or '<root>'),
      'schema_name: ' + schema_name,
      'msg: a definition shouldn\'t have both type and schema properties'
    ]]
    return error_msgs

  if next_schema:
    new_schema_info=schema_info_dict.get(next_schema)

    new_schema_data=dict(
      name=next_schema,
      ctx=schema_ctx,
      info=new_schema_info,
      dict=schema_info_dict,
      subelement=False,
      required=True
    )

    return validate_next_value(new_schema_data, value, error_msgs)

  is_list=isinstance(value, list)
  is_dict=isinstance(value, dict)
  is_string=isinstance(value, str)

  if schema_info.get('non_empty'):
    if is_list:
      if not len(value):
        error_msgs+=[[
          'at: ' + (schema_ctx or '<root>'),
          'schema_name: ' + schema_name,
          'msg: list is empty'
        ]]
        return error_msgs
    elif is_dict:
      if not len(value):
        error_msgs+=[[
          'at: ' + (schema_ctx or '<root>'),
          'schema_name: ' + schema_name,
          'msg: dict is empty'
        ]]
        return error_msgs
    else:
      if not str(value):
        error_msgs+=[[
          'at: ' + (schema_ctx or '<root>'),
          'schema_name: ' + schema_name,
          'msg: value is empty'
        ]]
        return error_msgs

  if value is not None:
    if not value_type:
      error_msgs+=[[
        'at: ' + (schema_ctx or '<root>'),
        'schema_name: ' + schema_name,
        'msg: type is not defined'
      ]]
      return error_msgs

    allowed_types=[
      'unknown',
      'primitive',
      'str',
      'bool',
      'int',
      'float',
      'str_or_dict',
      'dict',
      'map',
      'list'
    ]

    if value_type not in allowed_types:
      error_msgs+=[[
        'at: ' + (schema_ctx or '<root>'),
        'schema_name: ' + schema_name,
        'type: ' + value_type,
        'msg: type is invalid',
        'valid_types:',
        allowed_types
      ]]
      return error_msgs

    if value_type in ['list']:
      if not is_dict:
        error_msgs+=[[
          'at: ' + (schema_ctx or '<root>'),
          'schema_name: ' + schema_name,
          'type: ' + value_type,
          'msg: value expected to be a list'
        ]]
        return error_msgs
    elif value_type in ['dict', 'map']:
      if not is_dict:
        error_msgs+=[[
          'at: ' + (schema_ctx or '<root>'),
          'schema_name: ' + schema_name,
          'type: ' + value_type,
          'msg: value expected to be a dictionary'
        ]]
        return error_msgs
    elif value_type == 'str_or_dict':
      if (not is_string) and (not is_dict):
        error_msgs+=[[
          'at: ' + (schema_ctx or '<root>'),
          'schema_name: ' + schema_name,
          'type: ' + value_type,
          'msg: value expected to be a string or dictionary'
        ]]
        return error_msgs
    elif value_type == 'str':
      if not is_string:
        error_msgs+=[[
          'at: ' + (schema_ctx or '<root>'),
          'schema_name: ' + schema_name,
          'type: ' + value_type,
          'msg: value expected to be a string'
        ]]
        return error_msgs
    elif value_type != 'unknown':
      if is_list or is_dict:
        error_msgs+=[[
          'at: ' + (schema_ctx or '<root>'),
          'schema_name: ' + schema_name,
          'type: ' + value_type,
          'msg: value expected to be a primitive'
        ]]
        return error_msgs

    new_type=schema_info.get('type')
    new_schema_name=schema_info.get('schema')

    if (not new_type) and (not new_schema_name):
        error_msgs+=[[
          'at: ' + (schema_ctx or '<root>'),
          'schema_name: ' + schema_name,
          'msg: a property definition should have either a type or schema property'
        ]]
        return error_msgs
    elif new_type and new_schema_name:
        error_msgs+=[[
          'at: ' + (schema_ctx or '<root>'),
          'schema_name: ' + schema_name,
          'msg: a property definition shouldn\'t have both type and schema properties'
        ]]
        return error_msgs

    elem_type=schema_info.get('elem_type')
    elem_schema_name=schema_info.get('elem_schema')

    if value_type not in ['map', 'list']:
      if elem_type:
        error_msgs+=[[
          'at: ' + (schema_ctx or '<root>'),
          'schema_name: ' + schema_name,
          'msg: a definition should have elem_type only for lists and maps'
        ]]
        return error_msgs
      elif elem_schema_name:
        error_msgs+=[[
          'at: ' + (schema_ctx or '<root>'),
          'schema_name: ' + schema_name,
          'msg: a definition should have elem_schema only for lists and maps'
        ]]
        return error_msgs

    if value_type in ['map', 'list']:
      if (not elem_type) and (not elem_schema_name):
        error_msgs+=[[
          'at: ' + (schema_ctx or '<root>'),
          'schema_name: ' + schema_name,
          'msg: a property definition for a <' + value_type
            + '> should have either a elem_type or elem_schema property'
        ]]
        return error_msgs
      elif elem_type and elem_schema_name:
        error_msgs+=[[
          'at: ' + (schema_ctx or '<root>'),
          'schema_name: ' + schema_name,
          'msg: a property definition for a <' + value_type
            + '> shouldn\'t have both elem_type and elem_schema properties'
        ]]
        return error_msgs

    props=schema_info.get('props')

    if (not props) and (not is_subelement) and (value_type in ['dict', 'str_or_dict']):
        error_msgs+=[[
          'at: ' + (schema_ctx or '<root>'),
          'schema_name: ' + schema_name,
          'type: ' + value_type,
          'msg: props not defined for schema'
        ]]
        return error_msgs
    elif props and (value_type not in ['dict', 'str_or_dict']):
        error_msgs+=[[
          'at: ' + (schema_ctx or '<root>'),
          'schema_name: ' + schema_name,
          'type: ' + value_type,
          'msg: props should not be defined for a schema of this type'
        ]]
        return error_msgs
          
    if is_list:
      for idx, elem_value in enumerate(value):
        new_schema_info=dict(
          type=elem_type,
          schema=elem_schema_name,
          required=schema_info.get('elem_required'),
          non_empty=schema_info.get('non_empty')
        )

        new_schema_data=dict(
          name=schema_name,
          ctx=schema_ctx + '[' + idx + ']',
          info=new_schema_info,
          dict=schema_info_dict,
          subelement=True,
          required=new_schema_info.get('required')
        )

        error_msgs=validate_next_value(new_schema_data, elem_value, error_msgs)
    elif is_dict:
      for key in sorted(list(value.keys())):
        elem_value=value[key]

        if value_type in ['dict', 'str_or_dict']:
          if props:
            if key not in props:
              error_msgs+=[[
                'at: ' + (schema_ctx or '<root>'),
                'schema_name: ' + schema_name,
                'property: ' + key,
                'msg: property not defined in schema',
                'allowed: ',
                sorted(props.keys())
              ]]
              return error_msgs

            new_schema_info=props.get(key)

            new_schema_data=dict(
              name=schema_name,
              ctx=schema_ctx + (schema_ctx and '.') + key,
              info=new_schema_info,
              dict=schema_info_dict,
              subelement=True,
              required=new_schema_info.get('required')
            )

            error_msgs=validate_next_value(new_schema_data, elem_value, error_msgs)
        else:
          new_schema_info=dict(
            type=elem_type,
            schema=elem_schema_name,
            required=schema_info.get('elem_required'),
            non_empty=schema_info.get('non_empty')
          )

          new_schema_data=dict(
            name=schema_name,
            ctx=schema_ctx + '[' + key + ']',
            info=new_schema_info,
            dict=schema_info_dict,
            subelement=True,
            required=new_schema_info.get('required')
          )

          error_msgs=validate_next_value(new_schema_data, elem_value, error_msgs)
  
  return error_msgs

def validate_value(schema, value):
  if schema is None:
    return ['main schema is not defined']

  schema_name=schema.get('root')
  schema_info_dict=schema.get('schemas')
  schema_ctx=''
  error_msgs=[]
  
  schema_info=schema_info_dict.get(schema_name)

  schema_data=dict(
    name=schema_name,
    ctx=schema_ctx,
    info=schema_info,
    dict=schema_info_dict,
    subelement=False,
    required=True
  )

  error_msgs=validate_next_value(schema_data, value, error_msgs)

  return error_msgs

def prepare_error_msgs(error_msgs):
  new_error_msgs=[]
  separator="---------------------------------"

  for value in error_msgs:
    new_error_msgs+=[value, separator]

  return output_text(new_error_msgs)

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
        module.fail_json(msg='Error(s) when validating schema:\n\n' + prepare_error_msgs(error_msgs))

    error_msgs=validate_value(schema, value)

    if error_msgs:
      module.fail_json(msg='Error(s) when validating value:\n\n' + prepare_error_msgs(error_msgs))

    module.exit_json(changed=False)


if __name__ == '__main__':
    main()