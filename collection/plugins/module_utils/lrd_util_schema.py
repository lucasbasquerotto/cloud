#!/usr/bin/python

# (c) 2020, Lucas Basquerotto
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# pylint: disable=missing-module-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=import-error

from __future__ import absolute_import, division, print_function
__metaclass__ = type  # pylint: disable=invalid-name

from ansible_collections.lrd.cloud.plugins.module_utils.lrd_utils import (
    is_bool, is_int, is_float, is_str, load_yaml
)

SCHEMA_BASE = """
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
        schema: "type"
      alternative_type:
        schema: "type"
      main_schema:
        type: "str"
      alternative_schema:
        type: "str"
      non_empty:
        type: "bool"
      choices:
        type: "list"
        elem_type: "primitive"
      elem_type:
        type: "str"
      elem_alternative_type:
        schema: "type"
      elem_schema:
        type: "str"
      elem_main_schema:
        type: "str"
      elem_alternative_schema:
        type: "str"
      elem_required:
        type: "bool"
      elem_non_empty:
        type: "bool"
      elem_choices:
        type: "list"
        elem_type: "primitive"
      props:
        type: "map"
        elem_schema: "prop"
      lax:
        type: "bool"
  prop:
    type: "dict"
    props:
      type:
        schema: "type"
      alternative_type:
        schema: "type"
      schema:
        type: "str"
      main_schema:
        type: "str"
      alternative_schema:
        type: "str"
      required:
        type: "bool"
      non_empty:
        type: "bool"
      choices:
        type: "list"
        elem_type: "primitive"
      elem_type:
        type: "str"
      elem_alternative_type:
        schema: "type"
      elem_schema:
        type: "str"
      elem_main_schema:
        type: "str"
      elem_alternative_schema:
        type: "str"
      elem_required:
        type: "bool"
      elem_non_empty:
        type: "bool"
      elem_choices:
        type: "list"
        elem_type: "primitive"
  type:
    type: "str"
    choices:
      - "unknown"
      - "primitive"
      - "str"
      - "bool"
      - "int"
      - "float"
      - "dict"
      - "simple_dict"
      - "map"
      - "simple_map"
      - "list"
      - "simple_list"
"""


def by_value(item):
  return item[1]


def validate_next_value(schema_data, value):
  schema_name = schema_data.get('name')
  schema_ctx = schema_data.get('ctx')
  schema_info = schema_data.get('info')
  schema_info_dict = schema_data.get('dict')
  is_prop = schema_data.get('prop')
  is_subelement = schema_data.get('subelement')
  is_simple = schema_data.get('simple')
  required = schema_data.get('required')

  schema_suffix = ''

  if is_prop:
    schema_suffix = ' (prop)'
  elif is_subelement:
    schema_suffix = ' (subelement)'

  if schema_info is None:
    return [[
        str('schema_name: ' + schema_name + schema_suffix),
        str('at: ' + (schema_ctx or '<root>')),
        'msg: schema is not defined'
    ]]

  non_empty = schema_info.get('non_empty')

  if required or non_empty:
    if value is None:
      non_empty_info = ' (' + ('non_empty' if non_empty else 'required') + ')'

      return [[
          str('schema_name: ' + schema_name + schema_suffix),
          str('at: ' + (schema_ctx or '<root>')),
          str('msg: value is not defined' + non_empty_info)
      ]]

  if (not is_subelement) and (not is_prop) and (not is_simple) and ('schema' in schema_info):
    return [[
        str('schema_name: ' + schema_name + schema_suffix),
        str('at: ' + (schema_ctx or '<root>')),
        'msg: a schema definition should not have a schema property'
    ]]

  value_type = schema_info.get('type')
  next_schema = schema_info.get('schema')

  if (not value_type) and (not next_schema):
    return [[
        str('schema_name: ' + schema_name + schema_suffix),
        str('at: ' + (schema_ctx or '<root>')),
        'msg: a definition should have either a type or schema property'
    ]]
  elif value_type and next_schema:
    return [[
        str('schema_name: ' + schema_name + schema_suffix),
        str('at: ' + (schema_ctx or '<root>')),
        'msg: a definition should not have both type and schema properties'
    ]]

  if next_schema:
    new_schema_info = schema_info_dict.get(next_schema)

    new_schema_data = dict(
        name=next_schema,
        ctx=schema_ctx,
        info=new_schema_info,
        dict=schema_info_dict,
        prop=False,
        subelement=False,
        required=True
    )

    return validate_next_value(new_schema_data, value)

  new_type = schema_info.get('type')
  new_schema_name = schema_info.get('schema')

  if (not new_type) and (not new_schema_name):
    return [[
        str('schema_name: ' + schema_name + schema_suffix),
        str('at: ' + (schema_ctx or '<root>')),
        'msg: a property definition should have either a type or schema property'
    ]]
  elif new_type and new_schema_name:
    return [[
        str('schema_name: ' + schema_name + schema_suffix),
        str('at: ' + (schema_ctx or '<root>')),
        'msg: a property definition should not have both type and schema properties'
    ]]

  alternative_type = schema_info.get('alternative_type')
  main_schema = schema_info.get('main_schema')
  alternative_schema = schema_info.get('alternative_schema')

  if (value_type == 'simple_dict') and (not alternative_type) and (not alternative_schema):
    return [[
        str('schema_name: ' + schema_name + schema_suffix),
        str('at: ' + (schema_ctx or '<root>')),
        str('type: ' + value_type),
        'msg: a simple_dict must have an alternative type or alternative schema'
    ]]
  elif main_schema and (value_type != 'simple_dict'):
    return [[
        str('schema_name: ' + schema_name + schema_suffix),
        str('at: ' + (schema_ctx or '<root>')),
        str('type: ' + value_type),
        'msg: a main schema should be defined only for simple_dict'
    ]]
  elif alternative_type and (value_type != 'simple_dict'):
    return [[
        str('schema_name: ' + schema_name + schema_suffix),
        str('at: ' + (schema_ctx or '<root>')),
        str('type: ' + value_type),
        'msg: an alternative type should be defined only for simple_dict'
    ]]
  elif alternative_schema and (value_type != 'simple_dict'):
    return [[
        str('schema_name: ' + schema_name + schema_suffix),
        str('at: ' + (schema_ctx or '<root>')),
        str('type: ' + value_type),
        'msg: an alternative schema should be defined only for simple_dict'
    ]]
  elif alternative_type and alternative_schema:
    return [[
        str('schema_name: ' + schema_name + schema_suffix),
        str('at: ' + (schema_ctx or '<root>')),
        str('type: ' + value_type),
        'msg: define only an alternative type or alternative schema, not both'
    ]]

  elem_type = schema_info.get('elem_type')
  elem_alternative_type = schema_info.get('elem_alternative_type')
  elem_schema_name = schema_info.get('elem_schema')
  elem_main_schema = schema_info.get('elem_main_schema')
  elem_alternative_schema_name = schema_info.get('elem_alternative_schema')
  elem_required = schema_info.get('elem_required')
  elem_non_empty = schema_info.get('elem_non_empty')
  elem_choices = schema_info.get('elem_choices')

  if value_type not in ['map', 'simple_map', 'list', 'simple_list']:
    if elem_type:
      return [[
          str('schema_name: ' + schema_name + schema_suffix),
          str('at: ' + (schema_ctx or '<root>')),
          str('type: ' + value_type),
          'msg: a definition should have elem_type only for lists and maps'
      ]]
    elif elem_alternative_type:
      return [[
          str('schema_name: ' + schema_name + schema_suffix),
          str('at: ' + (schema_ctx or '<root>')),
          str('type: ' + value_type),
          'msg: a definition should have elem_alternative_type only for lists and maps'
      ]]
    elif elem_schema_name:
      return [[
          str('schema_name: ' + schema_name + schema_suffix),
          str('at: ' + (schema_ctx or '<root>')),
          str('type: ' + value_type),
          'msg: a definition should have elem_schema only for lists and maps'
      ]]
    elif elem_main_schema:
      return [[
          str('schema_name: ' + schema_name + schema_suffix),
          str('at: ' + (schema_ctx or '<root>')),
          str('type: ' + value_type),
          'msg: a definition should have elem_main_schema only for lists and maps'
      ]]
    elif elem_alternative_schema_name:
      return [[
          str('schema_name: ' + schema_name + schema_suffix),
          str('at: ' + (schema_ctx or '<root>')),
          str('type: ' + value_type),
          'msg: a definition should have elem_alternative_schema only for lists and maps'
      ]]
    elif elem_required:
      return [[
          str('schema_name: ' + schema_name + schema_suffix),
          str('at: ' + (schema_ctx or '<root>')),
          str('type: ' + value_type),
          'msg: a definition should have elem_required only for lists and maps'
      ]]
    elif elem_non_empty:
      return [[
          str('schema_name: ' + schema_name + schema_suffix),
          str('at: ' + (schema_ctx or '<root>')),
          str('type: ' + value_type),
          'msg: a definition should have elem_non_empty only for lists and maps'
      ]]
    elif elem_choices:
      return [[
          str('schema_name: ' + schema_name + schema_suffix),
          str('at: ' + (schema_ctx or '<root>')),
          str('type: ' + value_type),
          'msg: a definition should have elem_choices only for lists and maps'
      ]]

  if value_type in ['map', 'simple_map', 'list', 'simple_list']:
    if (not elem_type) and (not elem_schema_name):
      return [[
          str('schema_name: ' + schema_name + schema_suffix),
          str('at: ' + (schema_ctx or '<root>')),
          str('type: ' + value_type),
          'msg: a property definition with this type should have either a '
          + 'elem_type or elem_schema property'
      ]]
    elif elem_type and elem_schema_name:
      return [[
          str('schema_name: ' + schema_name + schema_suffix),
          str('at: ' + (schema_ctx or '<root>')),
          str('type: ' + value_type),
          'msg: a property definition with this type should not have '
          + 'both elem_type and elem_schema properties'
      ]]

  if value_type == 'simple_dict':
    invalid_alternative_types = ['map', 'simple_map', 'dict', 'simple_dict']

    if alternative_type and (alternative_type in invalid_alternative_types):
      return [[
          str('schema_name: ' + schema_name + schema_suffix),
          str('at: ' + (schema_ctx or '<root>')),
          str('type: ' + value_type),
          str('alternative_type: ' + alternative_type),
          str('msg: invalid alternative type for a ' + value_type),
          'invalid alternative types: ',
          invalid_alternative_types,
      ]]

    if alternative_schema:
      schema_info_aux = schema_info_dict.get(alternative_schema)
      schema_info_aux_type = (
          schema_info_aux.get('type') if schema_info_aux else None
      )

      if schema_info_aux_type and (schema_info_aux_type in invalid_alternative_types):
        return [[
            str('schema_name: ' + schema_name + schema_suffix),
            str('at: ' + (schema_ctx or '<root>')),
            str('type: ' + value_type),
            str('alternative schema type: ' + schema_info_aux_type),
            str('msg: invalid alternative schema type for a ' + value_type),
            'invalid alternative types: ',
            invalid_alternative_types,
        ]]
  elif value_type in ['simple_map', 'simple_list']:
    invalid_elem_types = (
        ['list', 'simple_list']
        if (value_type == 'simple_list')
        else ['map', 'simple_map', 'dict', 'simple_dict']
    )

    if elem_type and (elem_type in invalid_elem_types):
      return [[
          str('schema_name: ' + schema_name + schema_suffix),
          str('at: ' + (schema_ctx or '<root>')),
          str('type: ' + value_type),
          str('element type: ' + elem_type),
          str('msg: invalid element type for a ' + value_type),
          'invalid element types: ',
          invalid_elem_types,
      ]]

    if elem_schema_name:
      schema_info_aux = schema_info_dict.get(elem_schema_name)
      schema_info_aux_type = schema_info_aux.get(
          'type') if schema_info_aux else None

      if schema_info_aux_type and (schema_info_aux_type in invalid_elem_types):
        return [[
            str('schema_name: ' + schema_name + schema_suffix),
            str('at: ' + (schema_ctx or '<root>')),
            str('type: ' + value_type),
            str('element schema type: ' + schema_info_aux_type),
            str('msg: invalid element schema type for a ' + value_type),
            'invalid element types: ',
            invalid_elem_types,
        ]]

  props = schema_info.get('props')

  if (
      (not props)
      and
      (not is_prop)
      and
      (not is_subelement)
      and
      (value_type in ['dict', 'simple_dict'])
  ):
    if (value_type != 'simple_dict') or not main_schema:
      return [[
          str('schema_name: ' + schema_name + schema_suffix),
          str('at: ' + (schema_ctx or '<root>')),
          str('type: ' + value_type),
          'msg: props not defined for schema'
      ]]

  if props and is_prop:
    return [[
        str('schema_name: ' + schema_name + schema_suffix),
        str('at: ' + (schema_ctx or '<root>')),
        str('type: ' + value_type),
        'msg: props should not be defined inside a property (only in schemas)'
    ]]
  elif props and (value_type not in ['dict', 'simple_dict']):
    return [[
        str('schema_name: ' + schema_name + schema_suffix),
        str('at: ' + (schema_ctx or '<root>')),
        str('type: ' + value_type),
        'msg: props should not be defined for a schema of this type'
    ]]
  elif props and (value_type == 'simple_dict') and main_schema:
    return [[
        str('schema_name: ' + schema_name + schema_suffix),
        str('at: ' + (schema_ctx or '<root>')),
        str('type: ' + value_type),
        'msg: props should not be defined for a simple_dict with main_schema'
    ]]

  is_list = isinstance(value, list)
  is_dict = isinstance(value, dict)
  is_string = is_str(value)

  if non_empty:
    if is_list:
      if not value:
        return [[
            str('schema_name: ' + schema_name + schema_suffix),
            str('at: ' + (schema_ctx or '<root>')),
            'msg: list is empty'
        ]]
    elif is_dict:
      if not value:
        return [[
            str('schema_name: ' + schema_name + schema_suffix),
            str('at: ' + (schema_ctx or '<root>')),
            'msg: dict is empty'
        ]]
    else:
      if not str(value):
        return [[
            str('schema_name: ' + schema_name + schema_suffix),
            str('at: ' + (schema_ctx or '<root>')),
            'msg: value is empty'
        ]]

  if value is not None:
    if not value_type:
      return [[
          str('schema_name: ' + schema_name + schema_suffix),
          str('at: ' + (schema_ctx or '<root>')),
          'msg: type is not defined'
      ]]

    if value_type in ['list']:
      if not is_list:
        return [[
            str('schema_name: ' + schema_name + schema_suffix),
            str('at: ' + (schema_ctx or '<root>')),
            str('type: ' + value_type),
            str('value type: ' + str(type(value))),
            'msg: value expected to be a list',
        ]]
    elif value_type in ['dict', 'map']:
      if not is_dict:
        return [[
            str('schema_name: ' + schema_name + schema_suffix),
            str('at: ' + (schema_ctx or '<root>')),
            str('type: ' + value_type),
            str('value type: ' + str(type(value))),
            'msg: value expected to be a dictionary'
        ]]
    elif value_type == 'simple_dict':
      if not is_dict:
        new_schema_info = dict(
            type=alternative_type,
            schema=alternative_schema,
            required=required,
            non_empty=non_empty,
        )

        new_schema_data = dict(
            name=schema_name + ' (' + value_type + ' - alternative)',
            ctx=schema_ctx,
            info=new_schema_info,
            dict=schema_info_dict,
            prop=is_prop,
            subelement=is_subelement,
            required=required,
            simple=True,
        )

        return validate_next_value(new_schema_data, value)
    elif value_type in ['simple_map', 'simple_list']:
      if (
          ((value_type == 'simple_list') and not is_list)
          or
          ((value_type == 'simple_map') and not is_dict)
      ):

        new_schema_info = dict(
            type=elem_type,
            schema=elem_schema_name,
            required=elem_required,
            non_empty=elem_non_empty,
            choices=elem_choices,
        )

        new_schema_data = dict(
            name=schema_name + ' (' + value_type + ' - single)',
            ctx=schema_ctx,
            info=new_schema_info,
            dict=schema_info_dict,
            prop=is_prop,
            subelement=is_subelement,
            required=required,
            simple=True,
        )

        return validate_next_value(new_schema_data, value)
    elif value_type == 'str':
      if not is_string:
        return [[
            str('schema_name: ' + schema_name + schema_suffix),
            str('at: ' + (schema_ctx or '<root>')),
            str('type: ' + value_type),
            str('value type: ' + str(type(value))),
            'msg: value expected to be a string'
        ]]
    elif value_type != 'unknown':
      if is_list or is_dict:
        return [[
            str('schema_name: ' + schema_name + schema_suffix),
            str('at: ' + (schema_ctx or '<root>')),
            str('type: ' + value_type),
            str('value type: ' + str(type(value))),
            'msg: value expected to be a primitive'
        ]]

    primitive_types = [
        'primitive',
        'str',
        'bool',
        'int',
        'float',
    ]

    if value_type in primitive_types and (str(value) != ''):
      if (value_type == 'bool') and (not isinstance(value, bool)):
        if not is_bool(value):
          return [[
              str('schema_name: ' + schema_name + schema_suffix),
              str('at: ' + (schema_ctx or '<root>')),
              str('type: ' + value_type),
              str('value type: ' + str(type(value))),
              'msg: value should be a boolean',
          ]]
      elif (
          (value_type == 'int')
          and
          (isinstance(value, bool) or not isinstance(value, int))
      ):
        if (not is_str(value)) or (not is_int(value)):
          return [[
              str('schema_name: ' + schema_name + schema_suffix),
              str('at: ' + (schema_ctx or '<root>')),
              str('type: ' + value_type),
              str('value type: ' + str(type(value))),
              'msg: value should be an integer',
          ]]
      elif (value_type == 'float') and (not isinstance(value, float)):
        if (not is_str(value)) or (not is_float(value)):
          return [[
              str('schema_name: ' + schema_name + schema_suffix),
              str('at: ' + (schema_ctx or '<root>')),
              str('type: ' + value_type),
              str('value type: ' + str(type(value))),
              'msg: value should be a float',
          ]]

    choices = schema_info.get('choices')

    if choices:
      if value_type not in primitive_types:
        return [[
            str('schema_name: ' + schema_name + schema_suffix),
            str('at: ' + (schema_ctx or '<root>')),
            str('type: ' + value_type),
            'msg: value type is not primitive but has choices',
        ]]
      elif value not in choices:
        return [[
            str('schema_name: ' + schema_name + schema_suffix),
            str('at: ' + (schema_ctx or '<root>')),
            str('type: ' + value_type),
            str('value: ' + str(value)),
            'msg: value is invalid',
            'valid choices:',
            choices
        ]]

    if main_schema:
      new_schema_info = dict(
          schema=main_schema,
          required=required,
          non_empty=non_empty,
          prop=is_prop,
          subelement=is_subelement,
      )

      new_schema_data = dict(
          name=schema_name + ' (' + value_type + ' - main)',
          ctx=schema_ctx,
          info=new_schema_info,
          dict=schema_info_dict,
          required=required,
          simple=True,
      )

      return validate_next_value(new_schema_data, value)

    if value_type != 'unknown':
      error_msgs = []

      if is_list:
        for idx, elem_value in enumerate(value):
          new_schema_info = dict(
              type=elem_type,
              alternative_type=elem_alternative_type,
              schema=elem_schema_name,
              main_schema=elem_main_schema,
              alternative_schema=elem_alternative_schema_name,
              required=elem_required,
              non_empty=elem_non_empty,
              choices=elem_choices,
          )

          new_schema_data = dict(
              name=schema_name,
              ctx=schema_ctx + '[' + str(idx) + ']',
              info=new_schema_info,
              dict=schema_info_dict,
              prop=False,
              subelement=True,
              required=elem_required
          )

          error_msgs += validate_next_value(new_schema_data, elem_value)
      elif is_dict:
        keys = list(value.keys())

        # required or non-empty properties
        if props and (value_type in ['dict', 'simple_dict']):
          for key in list(props.keys()):
            prop_value = props.get(key)

            if prop_value and (prop_value.get('required') or prop_value.get('non_empty')):
              keys += [key]

          keys = list(set(keys))

        for key in sorted(keys):
          elem_value = value.get(key)

          if value_type in ['dict', 'simple_dict']:
            if props:
              if key not in props:
                if not schema_info.get('lax'):
                  error_msgs += [[
                      str('schema_name: ' + schema_name + schema_suffix),
                      str('at: ' + (schema_ctx or '<root>')),
                      str('property: ' + str(key)),
                      'msg: property not defined in schema',
                      'allowed: ',
                      sorted(props.keys())
                  ]]
              else:
                new_schema_info = props.get(key)

                new_schema_data = dict(
                    name=schema_name,
                    ctx=schema_ctx + (schema_ctx and '.') + key,
                    info=new_schema_info,
                    dict=schema_info_dict,
                    prop=True,
                    subelement=False,
                    required=new_schema_info.get('required')
                )

                error_msgs += validate_next_value(new_schema_data, elem_value)
          else:
            new_schema_info = dict(
                type=elem_type,
                alternative_type=elem_alternative_type,
                schema=elem_schema_name,
                main_schema=elem_main_schema,
                alternative_schema=elem_alternative_schema_name,
                required=elem_required,
                non_empty=elem_non_empty,
                choices=elem_choices,
            )

            new_schema_data = dict(
                name=schema_name,
                ctx=schema_ctx + '[' + key + ']',
                info=new_schema_info,
                dict=schema_info_dict,
                prop=False,
                subelement=True,
                required=elem_required
            )

            error_msgs += validate_next_value(new_schema_data, elem_value)

      return error_msgs

  return []


def validate_value(schema, value):
  if schema is None:
    return [['msg: main schema is not defined']]

  schema_name = schema.get('root')
  schema_info_dict = schema.get('schemas')
  schema_ctx = ''

  schema_info = schema_info_dict.get(schema_name)

  schema_data = dict(
      name=schema_name,
      ctx=schema_ctx,
      info=schema_info,
      dict=schema_info_dict,
      subelement=False,
      required=True
  )

  error_msgs = validate_next_value(schema_data, value)

  return error_msgs


def validate(schema, value, validate_schema=True):
  error_msgs = []

  if validate_schema:
    schema_base = load_yaml(SCHEMA_BASE)
    error_msgs_aux = validate_value(schema_base, schema)

    if error_msgs_aux:
      for value in (error_msgs_aux or []):
        new_value = ['schema context: schema'] + value
        error_msgs += [new_value]

      return error_msgs

  error_msgs_aux = validate_value(schema, value)

  if error_msgs_aux:
    for value in (error_msgs_aux or []):
      new_value = ['schema context: value'] + value
      error_msgs += [new_value]

    return error_msgs

  return []
