#!/usr/bin/python

# (c) 2020, Lucas Basquerotto
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# pylint: disable=missing-module-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=import-error
# pylint: disable=too-many-lines
# pylint: disable=broad-except

from __future__ import absolute_import, division, print_function
__metaclass__ = type  # pylint: disable=invalid-name

import os
import traceback

from ansible_collections.lrd.cloud.plugins.module_utils.lrd_utils import load_cached_file
from ansible_collections.lrd.cloud.plugins.module_utils.lrd_util_schema import validate_schema


def validate_ctx_schema(ctx_title, schema_files, task_data):
  error_msgs = list()

  try:
    task_data = task_data or dict()
    base_dir_prefix = task_data.get('base_dir_prefix')
    dict_to_validate = task_data.get('dict_to_validate')
    prop_names = task_data.get('prop_names')
    all_props = task_data.get('all_props')

    dict_to_validate = dict_to_validate or dict()

    if schema_files:
      if not isinstance(schema_files, list):
        schema_files = [schema_files]

      for schema_file in schema_files:
        schema_file = (
            (base_dir_prefix + schema_file)
            if base_dir_prefix
            else schema_file
        )

        if not schema_file:
          error_msgs += [[
              str('context: ' + str(ctx_title or '')),
              str('msg: schema file not defined'),
          ]]
        elif os.path.exists(schema_file):
          schema = load_cached_file(schema_file)

          schema_data = dict()

          if all_props:
            schema_data = dict_to_validate
          else:
            for key in (prop_names or []):
              if dict_to_validate.get(key) is not None:
                schema_data[key] = dict_to_validate.get(key)

          error_msgs_aux = validate_schema(
              schema, schema_data
          )

          for value in (error_msgs_aux or []):
            new_value = [
                str('context: ' + str(ctx_title or '')),
                str('schema file: ' + schema_file),
            ] + value
            error_msgs += [new_value]
        else:
          error_msgs += [[
              str('context: ' + str(ctx_title or '')),
              str('msg: schema file not found: ' + schema_file),
          ]]
    return dict(result=None, error_msgs=error_msgs)
  except Exception as error:
    error_msgs += [[
        str('context: ' + str(ctx_title or '')),
        'msg: error when trying to validate the context schema',
        'error type: ' + str(type(error)),
        'error details: ',
        traceback.format_exc(),
    ]]
    return dict(error_msgs=error_msgs)


def get_validators(ctx_title, validator_files, task_data, env_data):
  result = list()
  error_msgs = list()

  try:
    task_data = task_data or dict()
    base_dir_prefix = task_data.get('base_dir_prefix')
    dict_to_validate = task_data.get('dict_to_validate')
    prop_names = task_data.get('prop_names')
    all_props = task_data.get('all_props')

    env = env_data.get('env') or dict()
    meta = env.get('meta') or dict()
    dev = env_data.get('dev')
    ignore_validators = meta.get('ignore_validators')
    ignore_validators = (
        ignore_validators
        if (ignore_validators is not None)
        else dev
    )

    dict_to_validate = dict_to_validate or dict()

    if validator_files:
      dict_to_validate = dict_to_validate or dict()

      if not isinstance(validator_files, list):
        validator_files = [validator_files]

      for validator_file in validator_files:
        validator_file = (
            (base_dir_prefix + validator_file)
            if base_dir_prefix
            else validator_file
        )

        if not validator_file:
          error_msgs += [[
              str('context: ' + str(ctx_title or '')),
              str('msg: validator file not defined'),
          ]]
        elif os.path.exists(validator_file):
          if not ignore_validators:
            validator_data = dict()

            if all_props:
              validator_data = dict_to_validate
            else:
              for key in (prop_names or []):
                if dict_to_validate.get(key) is not None:
                  validator_data[key] = dict_to_validate.get(key)

            result_item = dict(
                task=validator_file,
                data=validator_data,
                base_dir_prefix=base_dir_prefix,
            )
            result += [result_item]
        else:
          error_msgs += [[
              str('context: ' + str(ctx_title or '')),
              str('msg: validator file not found: ' + validator_file),
          ]]

    return dict(result=result, error_msgs=error_msgs)
  except Exception as error:
    error_msgs += [[
        str('context: ' + str(ctx_title or '')),
        'msg: error when trying to get the context validators',
        'error type: ' + str(type(error)),
        'error details: ',
        traceback.format_exc(),
    ]]
    return dict(error_msgs=error_msgs)
