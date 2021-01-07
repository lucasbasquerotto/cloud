#!/usr/bin/python

# (c) 2020, Lucas Basquerotto
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# pylint: disable=missing-module-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=import-error
# pylint: disable=too-many-lines

from __future__ import absolute_import, division, print_function
__metaclass__ = type  # pylint: disable=invalid-name

import re

from ansible_collections.lrd.cloud.plugins.module_utils.lrd_utils import (
    is_bool, is_int, is_float, is_str, load_cached_file, to_float, to_int
)


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
        str('context: dynamic schema'),
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
        str('context: dynamic schema'),
        str('schema_name: ' + schema_name + schema_suffix),
        str('at: ' + (schema_ctx or '<root>')),
        'msg: a schema definition should not have a schema property'
    ]]

  value_type = schema_info.get('type')
  choices = schema_info.get('choices')
  regex = schema_info.get('regex')
  minimum = to_int(schema_info.get('min'))
  maximum = to_int(schema_info.get('max'))
  next_schema = schema_info.get('schema')

  if (not value_type) and (not next_schema):
    return [[
        str('context: dynamic schema'),
        str('schema_name: ' + schema_name + schema_suffix),
        str('at: ' + (schema_ctx or '<root>')),
        'msg: a definition should have either a type or schema property'
    ]]
  elif value_type and next_schema:
    return [[
        str('context: dynamic schema'),
        str('schema_name: ' + schema_name + schema_suffix),
        str('at: ' + (schema_ctx or '<root>')),
        'msg: a definition should not have both type and schema properties'
    ]]

  if not value_type:
    if choices:
      return [[
          str('context: dynamic schema'),
          str('schema_name: ' + schema_name + schema_suffix),
          str('at: ' + (schema_ctx or '<root>')),
          'msg: a definition should have choices only when type is defined'
      ]]
    elif regex:
      return [[
          str('context: dynamic schema'),
          str('schema_name: ' + schema_name + schema_suffix),
          str('at: ' + (schema_ctx or '<root>')),
          'msg: a definition should have regex only when type is defined'
      ]]
    elif minimum is not None:
      return [[
          str('context: dynamic schema'),
          str('schema_name: ' + schema_name + schema_suffix),
          str('at: ' + (schema_ctx or '<root>')),
          'msg: a definition should have min only when type is defined'
      ]]
    elif maximum is not None:
      return [[
          str('context: dynamic schema'),
          str('schema_name: ' + schema_name + schema_suffix),
          str('at: ' + (schema_ctx or '<root>')),
          'msg: a definition should have max only when type is defined'
      ]]

  primitive_types = [
      'primitive',
      'str',
      'bool',
      'int',
      'float',
  ]

  if choices and (value_type not in primitive_types):
    return [[
        str('context: dynamic schema'),
        str('schema_name: ' + schema_name + schema_suffix),
        str('at: ' + (schema_ctx or '<root>')),
        str('type: ' + value_type),
        'msg: value type is not primitive but has choices',
    ]]

  if regex and (value_type != 'str'):
    return [[
        str('context: dynamic schema'),
        str('schema_name: ' + schema_name + schema_suffix),
        str('at: ' + (schema_ctx or '<root>')),
        str('type: ' + value_type),
        'msg: regex should only be specified for a string (str) type',
    ]]

  valid_min_max_types = ['str', 'int', 'float']

  if value_type not in valid_min_max_types:
    if minimum is not None:
      return [[
          str('context: dynamic schema'),
          str('schema_name: ' + schema_name + schema_suffix),
          str('at: ' + (schema_ctx or '<root>')),
          str('type: ' + value_type),
          'msg: min is specified for an invalid type',
          'allowed types:',
          valid_min_max_types,
      ]]

    if maximum is not None:
      return [[
          str('context: dynamic schema'),
          str('schema_name: ' + schema_name + schema_suffix),
          str('at: ' + (schema_ctx or '<root>')),
          str('type: ' + value_type),
          'msg: max is specified for an invalid type',
          'allowed types:',
          valid_min_max_types,
      ]]

  alternative_type = schema_info.get('alternative_type')
  alternative_choices = schema_info.get('alternative_choices')
  alternative_regex = schema_info.get('alternative_regex')
  alternative_min = schema_info.get('alternative_min')
  alternative_max = schema_info.get('alternative_max')
  main_schema = schema_info.get('main_schema')
  alternative_schema = schema_info.get('alternative_schema')

  if (value_type == 'simple_dict') and (not alternative_type) and (not alternative_schema):
    return [[
        str('context: dynamic schema'),
        str('schema_name: ' + schema_name + schema_suffix),
        str('at: ' + (schema_ctx or '<root>')),
        str('type: ' + value_type),
        'msg: a simple_dict must have an alternative type or alternative schema'
    ]]
  elif main_schema and (value_type != 'simple_dict'):
    return [[
        str('context: dynamic schema'),
        str('schema_name: ' + schema_name + schema_suffix),
        str('at: ' + (schema_ctx or '<root>')),
        str('type: ' + value_type),
        'msg: a main schema should be defined only for simple_dict'
    ]]
  elif alternative_type and (value_type != 'simple_dict'):
    return [[
        str('context: dynamic schema'),
        str('schema_name: ' + schema_name + schema_suffix),
        str('at: ' + (schema_ctx or '<root>')),
        str('type: ' + value_type),
        'msg: an alternative type should be defined only for simple_dict'
    ]]
  elif alternative_schema and (value_type != 'simple_dict'):
    return [[
        str('context: dynamic schema'),
        str('schema_name: ' + schema_name + schema_suffix),
        str('at: ' + (schema_ctx or '<root>')),
        str('type: ' + value_type),
        'msg: an alternative schema should be defined only for simple_dict'
    ]]
  elif alternative_type and alternative_schema:
    return [[
        str('context: dynamic schema'),
        str('schema_name: ' + schema_name + schema_suffix),
        str('at: ' + (schema_ctx or '<root>')),
        str('type: ' + value_type),
        'msg: define only an alternative type or alternative schema, not both'
    ]]

  if not alternative_type:
    if alternative_choices:
      return [[
          str('context: dynamic schema'),
          str('schema_name: ' + schema_name + schema_suffix),
          str('at: ' + (schema_ctx or '<root>')),
          'msg: a definition should have alternative_choices only '
          + 'when alternative_type is defined'
      ]]
    elif alternative_regex:
      return [[
          str('context: dynamic schema'),
          str('schema_name: ' + schema_name + schema_suffix),
          str('at: ' + (schema_ctx or '<root>')),
          'msg: a definition should have alternative_regex only '
          + 'when alternative_type is defined'
      ]]
    elif alternative_min:
      return [[
          str('context: dynamic schema'),
          str('schema_name: ' + schema_name + schema_suffix),
          str('at: ' + (schema_ctx or '<root>')),
          'msg: a definition should have alternative_min only '
          + 'when alternative_type is defined'
      ]]
    elif alternative_max:
      return [[
          str('context: dynamic schema'),
          str('schema_name: ' + schema_name + schema_suffix),
          str('at: ' + (schema_ctx or '<root>')),
          'msg: a definition should have alternative_max only '
          + 'when alternative_type is defined'
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

  elem_type = schema_info.get('elem_type')
  elem_alternative_type = schema_info.get('elem_alternative_type')
  elem_alternative_choices = schema_info.get('elem_alternative_choices')
  elem_alternative_regex = schema_info.get('elem_alternative_regex')
  elem_alternative_min = schema_info.get('elem_alternative_min')
  elem_alternative_max = schema_info.get('elem_alternative_max')
  elem_schema_name = schema_info.get('elem_schema')
  elem_main_schema = schema_info.get('elem_main_schema')
  elem_alternative_schema_name = schema_info.get('elem_alternative_schema')
  elem_required = schema_info.get('elem_required')
  elem_non_empty = schema_info.get('elem_non_empty')
  elem_choices = schema_info.get('elem_choices')
  elem_regex = schema_info.get('elem_regex')
  elem_min = schema_info.get('elem_min')
  elem_max = schema_info.get('elem_max')

  if value_type not in ['map', 'simple_map', 'list', 'simple_list']:
    if elem_type:
      return [[
          str('context: dynamic schema'),
          str('schema_name: ' + schema_name + schema_suffix),
          str('at: ' + (schema_ctx or '<root>')),
          str('type: ' + value_type),
          'msg: a definition should have elem_type only for lists and maps'
      ]]

    if elem_alternative_type:
      return [[
          str('context: dynamic schema'),
          str('schema_name: ' + schema_name + schema_suffix),
          str('at: ' + (schema_ctx or '<root>')),
          str('type: ' + value_type),
          'msg: a definition should have elem_alternative_type only for lists and maps'
      ]]
    elif elem_alternative_choices:
      return [[
          str('context: dynamic schema'),
          str('schema_name: ' + schema_name + schema_suffix),
          str('at: ' + (schema_ctx or '<root>')),
          str('type: ' + value_type),
          'msg: a definition should have elem_alternative_choices only for lists and maps'
      ]]
    elif elem_alternative_regex:
      return [[
          str('context: dynamic schema'),
          str('schema_name: ' + schema_name + schema_suffix),
          str('at: ' + (schema_ctx or '<root>')),
          str('type: ' + value_type),
          'msg: a definition should have elem_alternative_regex only for lists and maps'
      ]]
    elif elem_alternative_min:
      return [[
          str('context: dynamic schema'),
          str('schema_name: ' + schema_name + schema_suffix),
          str('at: ' + (schema_ctx or '<root>')),
          str('type: ' + value_type),
          'msg: a definition should have elem_alternative_min only for lists and maps'
      ]]
    elif elem_alternative_max:
      return [[
          str('context: dynamic schema'),
          str('schema_name: ' + schema_name + schema_suffix),
          str('at: ' + (schema_ctx or '<root>')),
          str('type: ' + value_type),
          'msg: a definition should have elem_alternative_max only for lists and maps'
      ]]
    elif elem_schema_name:
      return [[
          str('context: dynamic schema'),
          str('schema_name: ' + schema_name + schema_suffix),
          str('at: ' + (schema_ctx or '<root>')),
          str('type: ' + value_type),
          'msg: a definition should have elem_schema only for lists and maps'
      ]]
    elif elem_main_schema:
      return [[
          str('context: dynamic schema'),
          str('schema_name: ' + schema_name + schema_suffix),
          str('at: ' + (schema_ctx or '<root>')),
          str('type: ' + value_type),
          'msg: a definition should have elem_main_schema only for lists and maps'
      ]]
    elif elem_alternative_schema_name:
      return [[
          str('context: dynamic schema'),
          str('schema_name: ' + schema_name + schema_suffix),
          str('at: ' + (schema_ctx or '<root>')),
          str('type: ' + value_type),
          'msg: a definition should have elem_alternative_schema only for lists and maps'
      ]]
    elif elem_required:
      return [[
          str('context: dynamic schema'),
          str('schema_name: ' + schema_name + schema_suffix),
          str('at: ' + (schema_ctx or '<root>')),
          str('type: ' + value_type),
          'msg: a definition should have elem_required only for lists and maps'
      ]]
    elif elem_non_empty:
      return [[
          str('context: dynamic schema'),
          str('schema_name: ' + schema_name + schema_suffix),
          str('at: ' + (schema_ctx or '<root>')),
          str('type: ' + value_type),
          'msg: a definition should have elem_non_empty only for lists and maps'
      ]]
    elif elem_choices:
      return [[
          str('context: dynamic schema'),
          str('schema_name: ' + schema_name + schema_suffix),
          str('at: ' + (schema_ctx or '<root>')),
          str('type: ' + value_type),
          'msg: a definition should have elem_choices only for lists and maps'
      ]]
    elif elem_regex:
      return [[
          str('context: dynamic schema'),
          str('schema_name: ' + schema_name + schema_suffix),
          str('at: ' + (schema_ctx or '<root>')),
          str('type: ' + value_type),
          'msg: a definition should have elem_regex only for lists and maps'
      ]]
    elif elem_min:
      return [[
          str('context: dynamic schema'),
          str('schema_name: ' + schema_name + schema_suffix),
          str('at: ' + (schema_ctx or '<root>')),
          str('type: ' + value_type),
          'msg: a definition should have elem_min only for lists and maps'
      ]]
    elif elem_max:
      return [[
          str('context: dynamic schema'),
          str('schema_name: ' + schema_name + schema_suffix),
          str('at: ' + (schema_ctx or '<root>')),
          str('type: ' + value_type),
          'msg: a definition should have elem_max only for lists and maps'
      ]]

  elem_type_default = elem_type or ''

  if (
      (elem_type_default == 'simple_dict')
      and
      (not elem_alternative_type)
      and
      (not elem_alternative_schema_name)
  ):
    return [[
        str('context: dynamic schema'),
        str('schema_name: ' + schema_name + schema_suffix),
        str('at: ' + (schema_ctx or '<root>')),
        str('elem_type: ' + elem_type_default),
        'msg: a simple_dict for elem_type must have an elem_alternative_type or '
        + 'elem_alternative_schema'
    ]]
  elif elem_main_schema and (elem_type_default != 'simple_dict'):
    return [[
        str('context: dynamic schema'),
        str('schema_name: ' + schema_name + schema_suffix),
        str('at: ' + (schema_ctx or '<root>')),
        str('elem_type: ' + elem_type_default),
        'msg: elem_main_schema should be defined only when elem_type '
        + 'is defined and is simple_dict'
    ]]
  elif elem_alternative_type and (elem_type_default != 'simple_dict'):
    return [[
        str('context: dynamic schema'),
        str('schema_name: ' + schema_name + schema_suffix),
        str('at: ' + (schema_ctx or '<root>')),
        str('elem_type: ' + elem_type_default),
        'msg: elem_alternative_type should be defined only when elem_type '
        + 'is defined and is simple_dict'
    ]]
  elif elem_alternative_schema_name and (elem_type_default != 'simple_dict'):
    return [[
        str('context: dynamic schema'),
        str('schema_name: ' + schema_name + schema_suffix),
        str('at: ' + (schema_ctx or '<root>')),
        str('elem_type: ' + elem_type_default),
        'msg: elem_alternative_schema should be defined only when elem_type '
        + 'is defined and is simple_dict'
    ]]
  elif elem_alternative_type and elem_alternative_schema_name:
    return [[
        str('context: dynamic schema'),
        str('schema_name: ' + schema_name + schema_suffix),
        str('at: ' + (schema_ctx or '<root>')),
        str('elem_type: ' + elem_type_default),
        'msg: define only one of elem_alternative_type or elem_alternative_schema, not both'
    ]]

  if not elem_alternative_type:
    if elem_alternative_choices:
      return [[
          str('context: dynamic schema'),
          str('schema_name: ' + schema_name + schema_suffix),
          str('at: ' + (schema_ctx or '<root>')),
          'msg: a definition should have elem_alternative_choices only '
          + 'when elem_alternative_type is defined'
      ]]
    elif elem_alternative_regex:
      return [[
          str('context: dynamic schema'),
          str('schema_name: ' + schema_name + schema_suffix),
          str('at: ' + (schema_ctx or '<root>')),
          'msg: a definition should have elem_alternative_regex only '
          + 'when elem_alternative_type is defined'
      ]]
    elif elem_alternative_min:
      return [[
          str('context: dynamic schema'),
          str('schema_name: ' + schema_name + schema_suffix),
          str('at: ' + (schema_ctx or '<root>')),
          'msg: a definition should have elem_alternative_min only '
          + 'when elem_alternative_type is defined'
      ]]
    elif elem_alternative_max:
      return [[
          str('context: dynamic schema'),
          str('schema_name: ' + schema_name + schema_suffix),
          str('at: ' + (schema_ctx or '<root>')),
          'msg: a definition should have elem_alternative_max only '
          + 'when elem_alternative_type is defined'
      ]]

  if value_type in ['map', 'simple_map', 'list', 'simple_list']:
    if (not elem_type) and (not elem_schema_name):
      return [[
          str('context: dynamic schema'),
          str('schema_name: ' + schema_name + schema_suffix),
          str('at: ' + (schema_ctx or '<root>')),
          str('type: ' + value_type),
          'msg: a property definition with this type should have either a '
          + 'elem_type or elem_schema property'
      ]]
    elif elem_type and elem_schema_name:
      return [[
          str('context: dynamic schema'),
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
          str('context: dynamic schema'),
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
            str('context: dynamic schema'),
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
          str('context: dynamic schema'),
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
            str('context: dynamic schema'),
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
          str('context: dynamic schema'),
          str('schema_name: ' + schema_name + schema_suffix),
          str('at: ' + (schema_ctx or '<root>')),
          str('type: ' + value_type),
          'msg: props not defined for schema'
      ]]

  if props and is_prop:
    return [[
        str('context: dynamic schema'),
        str('schema_name: ' + schema_name + schema_suffix),
        str('at: ' + (schema_ctx or '<root>')),
        str('type: ' + value_type),
        'msg: props should not be defined inside a property (only in schemas)'
    ]]
  elif props and (value_type not in ['dict', 'simple_dict']):
    return [[
        str('context: dynamic schema'),
        str('schema_name: ' + schema_name + schema_suffix),
        str('at: ' + (schema_ctx or '<root>')),
        str('type: ' + value_type),
        'msg: props should not be defined for a schema of this type'
    ]]
  elif props and (value_type == 'simple_dict') and main_schema:
    return [[
        str('context: dynamic schema'),
        str('schema_name: ' + schema_name + schema_suffix),
        str('at: ' + (schema_ctx or '<root>')),
        str('type: ' + value_type),
        'msg: props should not be defined for a simple_dict with main_schema'
    ]]

  if choices and regex:
    return [[
        str('context: dynamic schema'),
        str('schema_name: ' + schema_name + schema_suffix),
        str('at: ' + (schema_ctx or '<root>')),
        str('type: ' + value_type),
        'msg: when choices is specified, regex cannot be specified',
    ]]
  elif choices and (minimum is not None):
    return [[
        str('context: dynamic schema'),
        str('schema_name: ' + schema_name + schema_suffix),
        str('at: ' + (schema_ctx or '<root>')),
        str('type: ' + value_type),
        'msg: when choices is specified, min cannot be specified',
    ]]
  elif choices and (maximum is not None):
    return [[
        str('context: dynamic schema'),
        str('schema_name: ' + schema_name + schema_suffix),
        str('at: ' + (schema_ctx or '<root>')),
        str('type: ' + value_type),
        'msg: when choices is specified, max cannot be specified',
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
            choices=alternative_choices,
            regex=alternative_regex,
            min=alternative_min,
            max=alternative_max,
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
            alternative_type=elem_alternative_type,
            alternative_choices=elem_alternative_choices,
            alternative_regex=elem_alternative_regex,
            alternative_min=elem_alternative_min,
            alternative_max=elem_alternative_max,
            schema=elem_schema_name,
            required=elem_required,
            non_empty=elem_non_empty,
            choices=elem_choices,
            regex=elem_regex,
            min=elem_min,
            max=elem_max,
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

    if choices and (value not in choices):
      return [[
          str('schema_name: ' + schema_name + schema_suffix),
          str('at: ' + (schema_ctx or '<root>')),
          str('type: ' + value_type),
          str('value: ' + str(value)),
          'msg: value is invalid',
          'valid choices:',
          choices
      ]]

    if regex:
      pattern = re.compile(regex)

      if not pattern.search(value):
        return [[
            str('schema_name: ' + schema_name + schema_suffix),
            str('at: ' + (schema_ctx or '<root>')),
            str('type: ' + value_type),
            str('regex: ' + regex),
            'msg: value is invalid (not compatible with the regex specified)',
        ]]

    if minimum is not None:
      if value_type == 'str':
        if len(value) < minimum:
          return [[
              str('schema_name: ' + schema_name + schema_suffix),
              str('at: ' + (schema_ctx or '<root>')),
              str('type: ' + value_type),
              str('min: ' + str(minimum)),
              'msg: value is invalid (the length of the string is less than the minimum specified)',
          ]]
      elif value_type in ['int', 'float']:
        numeric_value = (
            to_int(value)
            if (value_type == 'int')
            else to_float(value)
        )

        if numeric_value < minimum:
          return [[
              str('schema_name: ' + schema_name + schema_suffix),
              str('at: ' + (schema_ctx or '<root>')),
              str('type: ' + value_type),
              str('min: ' + str(minimum)),
              'msg: value is invalid (numeric value is less than the minimum specified)',
          ]]
      else:
        return [[
            str('context: dynamic schema (unexpected)'),
            str('schema_name: ' + schema_name + schema_suffix),
            str('at: ' + (schema_ctx or '<root>')),
            str('type: ' + value_type),
            'msg: min property is not allowed with this value type',
            'allowed types:',
            ['str', 'int', 'float'],
        ]]

    if maximum is not None:
      if value_type == 'str':
        if len(value) > maximum:
          return [[
              str('schema_name: ' + schema_name + schema_suffix),
              str('at: ' + (schema_ctx or '<root>')),
              str('type: ' + value_type),
              str('max: ' + str(maximum)),
              'msg: value is invalid (the length of the string is more than the maximum specified)',
          ]]
      elif value_type in ['int', 'float']:
        numeric_value = (
            to_int(value)
            if (value_type == 'int')
            else to_float(value)
        )

        if numeric_value > maximum:
          return [[
              str('schema_name: ' + schema_name + schema_suffix),
              str('at: ' + (schema_ctx or '<root>')),
              str('type: ' + value_type),
              str('max: ' + str(maximum)),
              'msg: value is invalid (numeric value is more than the maximum specified)',
          ]]
      else:
        return [[
            str('context: dynamic schema (unexpected)'),
            str('schema_name: ' + schema_name + schema_suffix),
            str('at: ' + (schema_ctx or '<root>')),
            str('type: ' + value_type),
            'msg: max property is not allowed with this value type',
            'allowed types:',
            ['str', 'int', 'float'],
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
              alternative_choices=elem_alternative_choices,
              alternative_regex=elem_alternative_regex,
              alternative_min=elem_alternative_min,
              alternative_max=elem_alternative_max,
              schema=elem_schema_name,
              main_schema=elem_main_schema,
              alternative_schema=elem_alternative_schema_name,
              required=elem_required,
              non_empty=elem_non_empty,
              choices=elem_choices,
              regex=elem_regex,
              min=elem_min,
              max=elem_max,
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
                alternative_choices=elem_alternative_choices,
                alternative_regex=elem_alternative_regex,
                alternative_min=elem_alternative_min,
                alternative_max=elem_alternative_max,
                schema=elem_schema_name,
                main_schema=elem_main_schema,
                alternative_schema=elem_alternative_schema_name,
                required=elem_required,
                non_empty=elem_non_empty,
                choices=elem_choices,
                regex=elem_regex,
                min=elem_min,
                max=elem_max,
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


def validate_schema(schema, value, full_validation=True):
  error_msgs = []

  if full_validation:
    schema_base = load_cached_file('schemas/schema.yml')
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
