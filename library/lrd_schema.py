#!/usr/bin/python

# (c) 2020, Lucas Basquerotto
# Sponsored by Four Kitchens http://fourkitchens.com.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# pylint: disable=missing-module-docstring

from __future__ import absolute_import, division, print_function
__metaclass__ = type # pylint: disable=invalid-name


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
      non_empty:
        type: "bool"
      elem_type:
        type: "str"
      elem_schema:
        type: "str"
      elem_required:
        type: "bool"
      elem_non_empty:
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
      required:
        type: "bool"
      non_empty:
        type: "bool"
      elem_type:
        type: "str"
      elem_schema:
        type: "str"
      elem_required:
        type: "bool"
      elem_non_empty:
        type: "bool"
      values:
        type: "list"
        elem_type: "str"

"""

# pylint: disable=missing-function-docstring

import yaml # pylint: disable=wrong-import-position

from ansible.module_utils.basic import AnsibleModule # pylint: disable=wrong-import-position
from ansible.module_utils._text import to_text # pylint: disable=wrong-import-position

try:
  from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
  from yaml import Loader, Dumper

def by_value(item):
  return item[1]

def validate_next_value(schema_data, value):
  schema_name=schema_data.get('name')
  schema_ctx=schema_data.get('ctx')
  schema_info=schema_data.get('info')
  schema_info_dict=schema_data.get('dict')
  is_prop=schema_data.get('prop')
  is_subelement=schema_data.get('subelement')
  required=schema_data.get('required')

  schema_suffix=''

  if is_prop:
    schema_suffix=' (prop)'
  elif is_subelement:
    schema_suffix=' (subelement)'

  if schema_info is None:
    return [[
      'at: ' + (schema_ctx or '<root>'),
      'schema_name: ' + schema_name + schema_suffix,
      'msg: schema is not defined'
    ]]

  if required or schema_info.get('non_empty'):
    if value is None:
      return [[
        'at: ' + (schema_ctx or '<root>'),
        'schema_name: ' + schema_name + schema_suffix,
        'msg: value is not defined'
      ]]

  value_type=schema_info.get('type')
  next_schema=schema_info.get('schema')

  if (not is_subelement) and ('schema' in schema_info):
    return [[
      'at: ' + (schema_ctx or '<root>'),
      'schema_name: ' + schema_name + schema_suffix,
      'msg: a schema definition shouldn\'t have a schema property'
    ]]
  elif (not value_type) and (not next_schema):
    return [[
      'at: ' + (schema_ctx or '<root>'),
      'schema_name: ' + schema_name + schema_suffix,
      'msg: a definition should have either a type or schema property'
    ]]
  elif value_type and next_schema:
    return [[
      'at: ' + (schema_ctx or '<root>'),
      'schema_name: ' + schema_name + schema_suffix,
      'msg: a definition shouldn\'t have both type and schema properties'
    ]]

  if next_schema:
    new_schema_info=schema_info_dict.get(next_schema)

    new_schema_data=dict(
      name=next_schema,
      ctx=schema_ctx,
      info=new_schema_info,
      dict=schema_info_dict,
      prop=False,
      subelement=False,
      required=True
    )

    return validate_next_value(new_schema_data, value)

  is_list=isinstance(value, list)
  is_dict=isinstance(value, dict)
  is_string=isinstance(value, str)

  if schema_info.get('non_empty'):
    if is_list:
      if not value:
        return [[
          'at: ' + (schema_ctx or '<root>'),
          'schema_name: ' + schema_name + schema_suffix,
          'msg: list is empty'
        ]]
    elif is_dict:
      if not value:
        return [[
          'at: ' + (schema_ctx or '<root>'),
          'schema_name: ' + schema_name + schema_suffix,
          'msg: dict is empty'
        ]]
    else:
      if not str(value):
        return [[
          'at: ' + (schema_ctx or '<root>'),
          'schema_name: ' + schema_name + schema_suffix,
          'msg: value is empty'
        ]]

  if value is not None:
    if not value_type:
      return [[
        'at: ' + (schema_ctx or '<root>'),
        'schema_name: ' + schema_name + schema_suffix,
        'msg: type is not defined'
      ]]

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
      return [[
        'at: ' + (schema_ctx or '<root>'),
        'schema_name: ' + schema_name + schema_suffix,
        'type: ' + value_type,
        'msg: type is invalid',
        'valid_types:',
        allowed_types
      ]]

    if value_type in ['list']:
      if not is_list:
        return [[
          'at: ' + (schema_ctx or '<root>'),
          'schema_name: ' + schema_name + schema_suffix,
          'type: ' + value_type,
          'msg: value expected to be a list',
        ]]
    elif value_type in ['dict', 'map']:
      if not is_dict:
        return [[
          'at: ' + (schema_ctx or '<root>'),
          'schema_name: ' + schema_name + schema_suffix,
          'type: ' + value_type,
          'msg: value expected to be a dictionary'
        ]]
    elif value_type == 'str_or_dict':
      if (not is_string) and (not is_dict):
        return [[
          'at: ' + (schema_ctx or '<root>'),
          'schema_name: ' + schema_name + schema_suffix,
          'type: ' + value_type,
          'msg: value expected to be a string or dictionary'
        ]]
    elif value_type == 'str':
      if not is_string:
        return [[
          'at: ' + (schema_ctx or '<root>'),
          'schema_name: ' + schema_name + schema_suffix,
          'type: ' + value_type,
          'msg: value expected to be a string'
        ]]
    elif value_type != 'unknown':
      if is_list or is_dict:
        return [[
          'at: ' + (schema_ctx or '<root>'),
          'schema_name: ' + schema_name + schema_suffix,
          'type: ' + value_type,
          'msg: value expected to be a primitive'
        ]]

    new_type=schema_info.get('type')
    new_schema_name=schema_info.get('schema')

    if (not new_type) and (not new_schema_name):
      return [[
        'at: ' + (schema_ctx or '<root>'),
        'schema_name: ' + schema_name + schema_suffix,
        'msg: a property definition should have either a type or schema property'
      ]]
    elif new_type and new_schema_name:
      return [[
        'at: ' + (schema_ctx or '<root>'),
        'schema_name: ' + schema_name + schema_suffix,
        'msg: a property definition shouldn\'t have both type and schema properties'
      ]]

    elem_type=schema_info.get('elem_type')
    elem_schema_name=schema_info.get('elem_schema')
    elem_required=schema_info.get('elem_required')
    elem_non_empty=schema_info.get('elem_non_empty')

    if value_type not in ['map', 'list']:
      if elem_type:
        return [[
          'at: ' + (schema_ctx or '<root>'),
          'schema_name: ' + schema_name + schema_suffix,
          'type: ' + value_type,
          'msg: a definition should have elem_type only for lists and maps'
        ]]
      elif elem_schema_name:
        return [[
          'at: ' + (schema_ctx or '<root>'),
          'schema_name: ' + schema_name + schema_suffix,
          'type: ' + value_type,
          'msg: a definition should have elem_schema only for lists and maps'
        ]]
      elif elem_required:
        return [[
          'at: ' + (schema_ctx or '<root>'),
          'schema_name: ' + schema_name + schema_suffix,
          'type: ' + value_type,
          'msg: a definition should have elem_required only for lists and maps'
        ]]
      elif elem_non_empty:
        return [[
          'at: ' + (schema_ctx or '<root>'),
          'schema_name: ' + schema_name + schema_suffix,
          'type: ' + value_type,
          'msg: a definition should have elem_non_empty only for lists and maps'
        ]]

    if value_type in ['map', 'list']:
      if (not elem_type) and (not elem_schema_name):
        return [[
          'at: ' + (schema_ctx or '<root>'),
          'schema_name: ' + schema_name + schema_suffix,
          'type: ' + value_type,
          'msg: a property definition for a <' + value_type
            + '> should have either a elem_type or elem_schema property'
        ]]
      elif elem_type and elem_schema_name:
        return [[
          'at: ' + (schema_ctx or '<root>'),
          'schema_name: ' + schema_name + schema_suffix,
          'type: ' + value_type,
          'msg: a property definition for a <' + value_type
            + '> shouldn\'t have both elem_type and elem_schema properties'
        ]]

    props=schema_info.get('props')

    if (
			(not props)
			and
			(not is_prop)
			and
			(not is_subelement)
			and
			(value_type in ['dict', 'str_or_dict'])
		):
      return [[
        'at: ' + (schema_ctx or '<root>'),
        'schema_name: ' + schema_name + schema_suffix,
        'type: ' + value_type,
        'msg: props not defined for schema'
      ]]
    elif props and is_prop:
      return [[
        'at: ' + (schema_ctx or '<root>'),
        'schema_name: ' + schema_name + schema_suffix,
        'type: ' + value_type,
        'msg: props should not be defined inside a property (only in schemas)'
      ]]
    elif props and (value_type not in ['dict', 'str_or_dict']):
      return [[
        'at: ' + (schema_ctx or '<root>'),
        'schema_name: ' + schema_name + schema_suffix,
        'type: ' + value_type,
        'msg: props should not be defined for a schema of this type'
      ]]

    if value_type != 'unknown':
      error_msgs=[]

      if is_list:
        for idx, elem_value in enumerate(value):
          new_schema_info=dict(
            type=elem_type,
            schema=elem_schema_name,
            required=elem_required,
            non_empty=elem_non_empty
          )

          new_schema_data=dict(
            name=schema_name,
            ctx=schema_ctx + '[' + str(idx) + ']',
            info=new_schema_info,
            dict=schema_info_dict,
            prop=False,
            subelement=True,
            required=elem_required
          )

          error_msgs+=validate_next_value(new_schema_data, elem_value)
      elif is_dict:
        for key in sorted(list(value.keys())):
          elem_value=value[key]

          if value_type in ['dict', 'str_or_dict']:
            if props:
              if key not in props:
                error_msgs+=[[
                  'at: ' + (schema_ctx or '<root>'),
                  'schema_name: ' + schema_name + schema_suffix,
                  'property: ' + key,
                  'msg: property not defined in schema',
                  'allowed: ',
                  sorted(props.keys())
                ]]
              else:
                new_schema_info=props.get(key)

                new_schema_data=dict(
                  name=schema_name,
                  ctx=schema_ctx + (schema_ctx and '.') + key,
                  info=new_schema_info,
                  dict=schema_info_dict,
                  prop=True,
                  subelement=False,
                  required=new_schema_info.get('required')
                )

                error_msgs+=validate_next_value(new_schema_data, elem_value)
          else:
            new_schema_info=dict(
              type=elem_type,
              schema=elem_schema_name,
              required=elem_required,
              non_empty=elem_non_empty
            )

            new_schema_data=dict(
              name=schema_name,
              ctx=schema_ctx + '[' + key + ']',
              info=new_schema_info,
              dict=schema_info_dict,
              prop=False,
              subelement=True,
              required=elem_required
            )

            error_msgs+=validate_next_value(new_schema_data, elem_value)

      return error_msgs

  return []

def validate_value(schema, value):
  if schema is None:
    return ['main schema is not defined']

  schema_name=schema.get('root')
  schema_info_dict=schema.get('schemas')
  schema_ctx=''

  schema_info=schema_info_dict.get(schema_name)

  schema_data=dict(
    name=schema_name,
    ctx=schema_ctx,
    info=schema_info,
    dict=schema_info_dict,
    subelement=False,
    required=True
  )

  error_msgs=validate_next_value(schema_data, value)

  if error_msgs:
    error_msgs+=[[
      str(len(error_msgs)) + ' error(s) found'
    ]]

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
