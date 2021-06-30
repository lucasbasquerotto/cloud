#!/usr/bin/python

# (c) 2020, Lucas Basquerotto
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# pylint: disable=missing-module-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=import-error
# pylint: disable=broad-except

# pyright: reportUnusedImport=true
# pyright: reportUnusedVariable=true
# pyright: reportMissingImports=false

from __future__ import absolute_import, division, print_function
__metaclass__ = type  # pylint: disable=invalid-name

import os
import traceback

from ansible_collections.lrd.cloud.plugins.module_utils.lrd_utils import (
    is_str, load_file, load_cached_file, merge_dicts
)
from ansible_collections.lrd.cloud.plugins.module_utils.lrd_util_params_mixer import mix
from ansible_collections.lrd.cloud.plugins.module_utils.lrd_util_schema import validate_schema
from ansible_collections.lrd.cloud.plugins.module_utils.lrd_util_template import lookup
from ansible_collections.lrd.cloud.plugins.module_utils.lrd_util_validation import (
    validate_ctx_schema, get_validators
)


def load_content(content, env, run_info, input_params=None, custom_dir=None):
  try:
    result = None

    info = prepare_content(
        content,
        env=env,
        run_info=run_info,
        additional_info=dict(
            input_params=input_params,
            custom_dir=custom_dir,
        ),
    )

    prepared_content = info.get('result')
    validators = info.get('validators')
    error_msgs_aux = info.get('error_msgs') or list()

    if not error_msgs_aux:
      content_type = prepared_content.get('type')

      if content_type == 'str':
        params = prepared_content.get('params')
        result = params.get('value')
      elif content_type == 'file':
        content_file = prepared_content.get('file')
        result = load_file(content_file)
      elif content_type == 'template':
        plugin = run_info.get('plugin')
        ansible_vars = run_info.get('ansible_vars')

        content_file = prepared_content.get('file')
        input_prepared_params = prepared_content.get('input')
        params = prepared_content.get('params')
        credentials = prepared_content.get('credentials')
        contents = prepared_content.get('contents')

        result = lookup(
            plugin,
            ansible_vars,
            content_file,
            dict(
                input=input_prepared_params,
                params=params,
                credentials=credentials,
                contents=contents,
            ),
        )
      else:
        error_msgs_aux = [[
            str('type: ' + str(type(content))),
            'msg: invalid prepared content type',
        ]]

    error_msgs = list()

    for value in (error_msgs_aux or []):
      new_value = ['context: load content'] + value
      error_msgs += [new_value]

    validate = run_info.get('validate')
    final_result = dict(
        result=result,
        error_msgs=error_msgs,
    )

    if validate:
      final_result['meta'] = dict(validators=validators)

    return final_result
  except Exception as error:
    error_msgs = [[
        'msg: error when trying to load the content',
        'error type: ' + str(type(error)),
        'error details: ',
        traceback.format_exc().split('\n'),
    ]]
    return dict(error_msgs=error_msgs)


def prepare_content(content, env, run_info, additional_info=None):
  result = dict()
  error_msgs = list()

  try:
    additional_info = additional_info or dict()

    input_params = additional_info.get('input_params')
    custom_dir = additional_info.get('custom_dir')
    parent_content_info = additional_info.get('parent_content_info')
    content_names = additional_info.get('content_names')

    if env is None:
      error_msgs += [['msg: environment variable not specified']]
      return dict(error_msgs=error_msgs)
    elif not isinstance(env, dict):
      error_msgs += [[
          str('env type: ' + str(type(env))),
          'msg: environment variable is not a dictionary',
      ]]
      return dict(error_msgs=error_msgs)

    if content is None:
      error_msgs += [['msg: content not specified']]
      return dict(error_msgs=error_msgs)

    if is_str(content):
      content = dict(
          type='str',
          params=dict(value=content)
      )

    if isinstance(content, dict):
      error_msgs_aux = list()

      env_data = run_info.get('env_data')
      validate = run_info.get('validate')

      content_type = content.get('type')

      if content_type == 'env':
        allowed_props = [
            'type',
            'name',
            'key',
            'credentials',
            'contents',
            'params',
            'group_params',
            'shared_params',
            'shared_group_params',
        ]
        required_props = [
            'type',
            'name',
        ]
      elif content_type == 'str':
        allowed_props = [
            'type',
            'params',
            'group_params',
            'shared_params',
            'shared_group_params',
        ]
        required_props = ['type']
      elif content_type == 'template':
        allowed_props = [
            'type',
            'origin',
            'file',
            'schema',
            'validator',
            'credentials',
            'contents',
            'params',
            'group_params',
            'shared_params',
            'shared_group_params',
        ]
        required_props = [
            'type',
            'file',
        ]
      else:
        content_type = 'file'
        allowed_props = [
            'type',
            'origin',
            'file',
        ]
        required_props = ['file']

      for prop in sorted(list(content.keys())):
        if prop not in allowed_props:
          error_msgs_aux += [[
              str('property: ' + prop),
              'msg: invalid property defined for the content',
              'allowed: ',
              allowed_props,
          ]]

      for prop in sorted(required_props):
        if not content.get(prop):
          error_msgs_aux += [[
              str('property: ' + prop),
              'msg: required property not defined for the content or empty',
          ]]

      if parent_content_info and (content_type != 'env'):
        parent_credentials = parent_content_info.get('credentials')
        parent_contents = parent_content_info.get('contents')
        parent_params = parent_content_info.get('params')

        if content_type != 'template':
          if parent_credentials:
            error_msgs_aux += [[
                str('property: ' + prop),
                'msg: credentials defined in a parent content (type=env), '
                + 'but child type does not accept credentials',
            ]]

          if parent_contents:
            error_msgs_aux += [[
                str('property: ' + prop),
                'msg: contents defined in a parent content (type=env), '
                + 'but child type does not accept contents',
            ]]

        if content_type not in ['str', 'template']:
          if parent_params:
            error_msgs_aux += [[
                str('property: ' + prop),
                'msg: parameters defined in a parent content (type=env), '
                + 'but child type does not accept params',
            ]]

      if not error_msgs_aux:
        content_origin = content.get('origin') or 'custom'
        allowed_origins = ['env', 'cloud', 'custom']

        if content_origin not in allowed_origins:
          error_msgs_aux += [[
              str('content origin: ' + content_origin),
              'msg: invalid content origin',
              'allowed:',
              allowed_origins,
          ]]

      credentials_dict = None
      inner_contents = None
      content_params = None

      if not error_msgs_aux:
        if content_type in ['env', 'template']:
          credentials_info_dict = (
              parent_content_info or dict()
          ).get('credentials')
          credentials_dict = content.get('credentials')

          if credentials_info_dict:
            credentials_dict = merge_dicts(
                credentials_dict, credentials_info_dict)

          inner_contents_info = (parent_content_info or dict()).get('contents')
          inner_contents = content.get('contents')

          if inner_contents_info:
            inner_contents = merge_dicts(inner_contents, inner_contents_info)

        if content_type in ['env', 'str', 'template']:
          result_aux_info = None
          error_msgs_aux_params = list()

          if parent_content_info:
            params_args = dict(
                params=parent_content_info.get('params'),
                group_params=parent_content_info.get('group_params'),
                shared_params=parent_content_info.get('shared_params'),
                shared_group_params=parent_content_info.get(
                    'shared_group_params'),
                shared_group_params_dict=env.get(
                    'content_shared_group_params'),
                shared_params_dict=env.get('content_shared_params'),
                group_params_dict=env.get('content_group_params'),
            )

            info = mix(params_args)

            result_aux_info = info.get('result')
            error_msgs_aux_info = info.get('error_msgs') or list()

            for value in (error_msgs_aux_info or []):
              new_value = ['context: content info params'] + value
              error_msgs_aux_params += [new_value]

          params_args = dict(
              params=content.get('params'),
              group_params=content.get('group_params'),
              shared_params=content.get('shared_params'),
              shared_group_params=content.get('shared_group_params'),
              shared_group_params_dict=env.get(
                  'content_shared_group_params'),
              shared_params_dict=env.get('content_shared_params'),
              group_params_dict=env.get('content_group_params'),
          )

          info = mix(params_args)

          result_aux_content = info.get('result')
          error_msgs_aux_content = info.get('error_msgs') or list()

          for value in (error_msgs_aux_content or []):
            new_value = ['context: content params'] + value
            error_msgs_aux_params += [new_value]

          error_msgs_aux += error_msgs_aux_params or []

          if not error_msgs_aux_params:
            content_params = merge_dicts(
                result_aux_content, result_aux_info) or None

      if not error_msgs_aux:
        if content_type == 'env':
          error_msgs_env = list()

          content_name = content.get('name')
          content_key = content.get('key') or content_name
          content_description = (
              (content_name + ' (' + content_key + ')')
              if content_name != content_key
              else content_name
          )

          content_names = content_names or set()

          if content_name in content_names:
            error_msgs_env += [['msg: content env with duplicate name']]

          if not error_msgs_env:
            content_names.add(content_name)
            contents = env.get('contents')

            if not contents:
              error_msgs_env += [['msg: no content specified for the environment']]
            elif not contents.get(content_key):
              error_msgs_env += [['msg: the content is not specified for the environment']]
            else:
              child_content = contents.get(content_key)
              child_additional_info = dict(
                  input_params=input_params,
                  custom_dir=custom_dir,
                  parent_content_info=dict(
                      credentials=credentials_dict,
                      contents=inner_contents,
                      params=content_params,
                  ),
                  content_names=content_names,
              )

              try:
                info = prepare_content(
                    child_content,
                    env=env,
                    run_info=run_info,
                    additional_info=child_additional_info,
                )

                result = info.get('result')
                error_msgs_env += info.get('error_msgs') or list()
              except Exception as error:
                error_msgs_env += [[
                    'msg: error when trying to prepare the content child (env type)',
                    'error type: ' + str(type(error)),
                    'error details: ',
                    traceback.format_exc().split('\n'),
                ]]

          for value in (error_msgs_env or []):
            new_value = [str('content: ' + content_description)] + value
            error_msgs_aux += [new_value]
        else:
          origin_dir_map = dict(
              cloud='',
              env=env_data.get('env_dir'),
              custom=custom_dir or '',
          )

          base_dir = origin_dir_map.get(content_origin)
          base_dir_prefix = (base_dir + '/') if base_dir else base_dir

          result['type'] = content_type
          result['params'] = content_params

          if content_type == 'template':
            result['input'] = input_params or None

            params_args = dict(
                group_params=credentials_dict,
                group_params_dict=env.get('credentials'),
            )

            info = mix(params_args)

            credentials = info.get('result')
            error_msgs_aux_credentials = info.get('error_msgs') or list()

            for value in (error_msgs_aux_credentials or []):
              new_value = ['context: content credentials'] + value
              error_msgs_aux += [new_value]

            if not error_msgs_aux_credentials:
              result['credentials'] = credentials or None

            prepared_inner_contents = dict()

            for inner_content_key in sorted(list((inner_contents or dict()).keys())):
              inner_content = inner_contents.get(inner_content_key)

              info = load_content(
                  inner_content,
                  env=env,
                  run_info=run_info,
                  input_params=input_params,
                  custom_dir=custom_dir,
              )

              prepared_inner_content = info.get('result')
              error_msgs_aux_content = info.get('error_msgs') or list()

              for value in (error_msgs_aux_content or []):
                new_value = [
                    str('inner content: ' + inner_content_key)] + value
                error_msgs_aux += [new_value]

              if not error_msgs_aux_content:
                prepared_inner_contents[inner_content_key] = prepared_inner_content

            result['contents'] = prepared_inner_contents or None

          if content_type in ['file', 'template']:
            file_rel = content.get('file')
            file_path = base_dir_prefix + file_rel
            result['file'] = file_path

            if validate and (not os.path.exists(file_path)):
              error_msgs_aux += [[
                  str('content origin: ' + content_origin),
                  str('msg: content file not found: ' + file_rel),
              ]]

          if validate and not error_msgs_aux:
            base_dir_prefix_schema = base_dir_prefix
            schema_files = content.get('schema')

            if content_type == 'str':
              base_dir_prefix_schema = None
              schema_files = ['schemas/content_str.schema.yml']

            task_data = dict(
                base_dir_prefix=base_dir_prefix_schema,
                dict_to_validate=result,
                prop_names=['input', 'params', 'credentials', 'contents'],
            )

            task_data['base_dir_prefix'] = base_dir_prefix_schema
            info = validate_ctx_schema(
                ctx_title='validate content schema',
                schema_files=schema_files,
                task_data=task_data,
            )
            task_data['base_dir_prefix'] = base_dir_prefix
            error_msgs_aux += (info.get('error_msgs') or [])

            info = get_validators(
                ctx_title='content validators',
                validator_files=content.get('validator'),
                task_data=task_data,
                env_data=env_data,
            )
            validators = info.get('result')
            error_msgs_aux += (info.get('error_msgs') or [])
            result['validators'] = validators or None

          if validate and not error_msgs_aux:
            schema_files = content.get('schema')

            if content_type == 'str':
              schema_files = ['schemas/content_str.schema.yml']

            if schema_files:
              if not isinstance(schema_files, list):
                schema_files = [schema_files]

              for schema_file in schema_files:
                if content_type != 'str':
                  schema_file = base_dir_prefix + schema_file

                if os.path.exists(schema_file):
                  schema = load_cached_file(schema_file)

                  schema_data = dict()

                  for key in ['input', 'params', 'credentials', 'contents']:
                    if result.get(key) is not None:
                      schema_data[key] = result.get(key)

                  error_msgs_aux_validate = validate_schema(
                      schema, schema_data
                  )

                  for value in (error_msgs_aux_validate or []):
                    new_value = [
                        'context: validate content schema',
                        str('schema file: ' + schema_file),
                    ] + value
                    error_msgs_aux += [new_value]
                else:
                  error_msgs_aux += [[
                      'context: validate content schema',
                      str('msg: schema file not found: ' + schema_file),
                  ]]

      for value in (error_msgs_aux or []):
        new_value = [str('content type: ' + content_type)] + value
        error_msgs += [new_value]

      if error_msgs:
        result = None
      else:
        result_keys = list(result.keys())

        for key in result_keys:
          if result.get(key) is None:
            result.pop(key, None)

      return dict(result=result, error_msgs=error_msgs)
    else:
      error_msgs += [[
          str('type: ' + str(type(content))),
          'msg: invalid content type',
      ]]
      return dict(error_msgs=error_msgs)
  except Exception as error:
    error_msgs += [[
        'msg: error when trying to prepare the content',
        'error type: ' + str(type(error)),
        'error details: ',
        traceback.format_exc().split('\n'),
    ]]
    return dict(error_msgs=error_msgs)
