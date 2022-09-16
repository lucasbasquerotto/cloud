#!/usr/bin/python

# (c) 2020, Lucas Basquerotto
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# pylint: disable=missing-module-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=import-error
# pylint: disable=too-many-lines
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


def prepare_mixed_data(context_full_info, params_dicts, run_info):
  result = dict()
  error_msgs = []

  try:
    ### Credentials ###

    info = prepare_mixed_credentials(context_full_info, run_info)

    result_aux = info.get('result') or dict()
    error_msgs_aux = info.get('error_msgs') or list()

    for value in (error_msgs_aux or []):
      new_value = ['context: mixed data (credentials)'] + value
      error_msgs += [new_value]

    if not error_msgs_aux:
      result['credentials'] = result_aux.get('credentials') or None

    ### Params ###

    info = prepare_mixed_params(context_full_info, params_dicts, run_info)

    result_aux = info.get('result')
    error_msgs_aux = info.get('error_msgs') or list()

    for value in (error_msgs_aux or []):
      new_value = ['context: mixed data (params)'] + value
      error_msgs += [new_value]

    if not error_msgs_aux:
      result['params'] = result_aux.get('params') or None

    ### Contents ###

    info = prepare_mixed_loaded_contents(context_full_info, run_info)

    result_aux = info.get('result')
    error_msgs_aux = info.get('error_msgs') or list()

    for value in (error_msgs_aux or []):
      new_value = ['context: mixed data (contents)'] + value
      error_msgs += [new_value]

    if not error_msgs_aux:
      result['contents'] = result_aux.get('contents') or None
      result['validators'] = result_aux.get('validators') or None

    return dict(result=result, error_msgs=error_msgs)
  except Exception as error:
    error_msgs += [[
        'msg: error when trying to prepare mixed data',
        'error type: ' + str(type(error)),
        'error details: ',
        traceback.format_exc().split('\n'),
    ]]
    return dict(error_msgs=error_msgs)


def prepare_mixed_credentials(context_full_info, run_info):
  result = dict()
  error_msgs = []

  try:
    context_data = context_full_info.get('data')
    context_info = context_full_info.get('info')
    context_ctx_info = context_full_info.get('ctx_info')

    env_data = run_info.get('env_data')
    services_data = run_info.get('services_data')

    env = env_data.get('env')

    ### Credentials ###

    result_aux_ctx_info = None
    result_aux_info = None
    error_msgs_aux = []

    credentials_dict = context_data.get('credentials')
    dynamic_credentials_dict = context_data.get('dynamic_credentials')
    credentials_env_dict = env.get('credentials')

    ### Credentials - Ctx Info ###

    if context_ctx_info:
      credentials_ctx_info_dict = context_ctx_info.get('credentials')
      dynamic_credentials_ctx_info_dict = context_ctx_info.get(
          'dynamic_credentials'
      )

      dynamic_credentials_info = dict()

      for credential_key in (dynamic_credentials_ctx_info_dict or dict()):
        if credentials_ctx_info_dict.get(credential_key):
          error_msgs_aux += [[
              'context: duplicate credential ctx info key',
              'credential_key: ' + credential_key,
              'msg: duplicate credential key '
              + '(defined both in credentials and dynamic_credentials)',
          ]]
        else:
          service_info = dynamic_credentials_ctx_info_dict.get(credential_key)
          service_name = service_info
          service_credential_name = credential_key

          if isinstance(service_info, dict):
            service_name = service_info.get('name')
            service_credential_name = service_info.get(
                'credential'
            ) or credential_key

          service_inner_data = services_data.get(service_name) or dict()
          service_data_credentials = service_inner_data.get(
              'credentials'
          ) or dict()
          credential_value = service_data_credentials.get(
              service_credential_name
          )

          if credential_value is not None:
            dynamic_credentials_info[credential_key] = credential_value

      params_args = dict(
          params=dynamic_credentials_info,
          group_params=credentials_ctx_info_dict,
          group_params_dict=credentials_env_dict,
      )

      info = mix(params_args)

      result_aux_ctx_info = info.get('result')
      error_msgs_aux_ctx_info = info.get('error_msgs') or list()

      for value in (error_msgs_aux_ctx_info or []):
        new_value = ['context: ctx info params'] + value
        error_msgs_aux += [new_value]

    ### Credentials - Info ###

    if isinstance(context_info, dict):
      credentials_info_dict = context_info.get('credentials')
      dynamic_credentials_info_dict = context_info.get(
          'dynamic_credentials'
      )

      dynamic_credentials_info = dict()

      for credential_key in (dynamic_credentials_info_dict or dict()):
        if credentials_info_dict.get(credential_key):
          error_msgs_aux += [[
              'context: duplicate credential info key',
              'credential_key: ' + credential_key,
              'msg: duplicate credential key '
              + '(defined both in credentials and dynamic_credentials)',
          ]]
        else:
          service_info = dynamic_credentials_info_dict.get(credential_key)
          service_name = service_info
          service_credential_name = credential_key

          if isinstance(service_info, dict):
            service_name = service_info.get('name')
            service_credential_name = service_info.get(
                'credential'
            ) or credential_key

          service_inner_data = services_data.get(service_name) or dict()
          service_data_credentials = service_inner_data.get(
              'credentials'
          ) or dict()
          credential_value = service_data_credentials.get(
              service_credential_name
          )

          if credential_value is not None:
            dynamic_credentials_info[credential_key] = credential_value

      params_args = dict(
          params=dynamic_credentials_info,
          group_params=credentials_info_dict,
          group_params_dict=credentials_env_dict,
      )

      info = mix(params_args)

      result_aux_info = info.get('result')
      error_msgs_aux_info = info.get('error_msgs') or list()

      for value in (error_msgs_aux_info or []):
        new_value = ['context: info credentials'] + value
        error_msgs_aux += [new_value]

    ### Credentials - Main ###

    dynamic_credentials_data = dict()

    for credential_key in (dynamic_credentials_dict or dict()):
      if credentials_dict.get(credential_key):
        error_msgs_aux += [[
            'context: duplicate credential key',
            'credential_key: ' + credential_key,
            'msg: duplicate credential key '
            + '(defined both in credentials and dynamic_credentials)',
        ]]
      else:
        service_info = dynamic_credentials_dict.get(credential_key)
        service_name = service_info
        service_credential_name = credential_key

        if isinstance(service_info, dict):
          service_name = service_info.get('name')
          service_credential_name = service_info.get(
              'credential'
          ) or credential_key

        service_inner_data = services_data.get(service_name) or dict()
        service_data_credentials = service_inner_data.get(
            'credentials'
        ) or dict()
        credential_value = service_data_credentials.get(
            service_credential_name
        )

        if credential_value is not None:
          dynamic_credentials_data[credential_key] = credential_value

    params_args = dict(
        params=dynamic_credentials_data,
        group_params=credentials_dict,
        group_params_dict=credentials_env_dict,
    )

    info = mix(params_args)

    result_aux = info.get('result')
    error_msgs_aux += info.get('error_msgs') or list()

    for value in error_msgs_aux:
      new_value = ['context: credentials'] + value
      error_msgs += [new_value]

    if not error_msgs:
      credentials = merge_dicts(
          result_aux, result_aux_info, result_aux_ctx_info
      )
      result['credentials'] = credentials or None

    return dict(result=result, error_msgs=error_msgs)
  except Exception as error:
    error_msgs += [[
        'msg: error when trying to prepare mixed credentials',
        'error type: ' + str(type(error)),
        'error details: ',
        traceback.format_exc().split('\n'),
    ]]
    return dict(error_msgs=error_msgs)


def prepare_mixed_params(context_full_info, params_dicts, run_info):
  result = dict()
  error_msgs = []

  try:
    context_data = context_full_info.get('data')
    context_info = context_full_info.get('info')
    context_ctx_info = context_full_info.get('ctx_info')

    shared_group_params_dict = params_dicts.get('shared_group_params_dict')
    shared_params_dict = params_dicts.get('shared_params_dict')
    group_params_dict = params_dicts.get('group_params_dict')

    services_data = run_info.get('services_data')

    ### Params ###

    result_aux_ctx_info = None
    result_aux_info = None
    error_msgs_aux = []

    params_dict = context_data.get('params')
    dynamic_params_dict = context_data.get('dynamic_params')

    ### Params - Ctx Info ###

    if context_ctx_info:
      params_ctx_info_dict = context_ctx_info.get('params')
      dynamic_params_ctx_info_dict = context_ctx_info.get(
          'dynamic_params'
      )

      dynamic_params_info = dict()

      for param_key in (dynamic_params_ctx_info_dict or dict()):
        if params_ctx_info_dict.get(param_key):
          error_msgs_aux += [[
              'context: duplicate param ctx info key',
              'param_key: ' + param_key,
              'msg: duplicate param key '
              + '(defined both in params and dynamic_params)',
          ]]
        else:
          service_info = dynamic_params_ctx_info_dict.get(param_key)
          service_name = service_info
          service_param_name = param_key

          if isinstance(service_info, dict):
            service_name = service_info.get('name')
            service_param_name = service_info.get(
                'param'
            ) or param_key

          service_inner_data = services_data.get(service_name) or dict()
          service_data_params = service_inner_data.get(
              'params'
          ) or dict()
          param_value = service_data_params.get(
              service_param_name
          )

          if param_value is not None:
            dynamic_params_info[param_key] = param_value

      params_args = dict(
          params=merge_dicts(dynamic_params_info, params_ctx_info_dict),
          group_params=context_ctx_info.get('group_params'),
          shared_params=context_ctx_info.get('shared_params'),
          shared_group_params=context_ctx_info.get('shared_group_params'),
          shared_group_params_dict=shared_group_params_dict,
          shared_params_dict=shared_params_dict,
          group_params_dict=group_params_dict,
      )

      info = mix(params_args)

      result_aux_ctx_info = info.get('result')
      error_msgs_aux_ctx_info = info.get('error_msgs') or list()

      for value in (error_msgs_aux_ctx_info or []):
        new_value = ['context: ctx info params'] + value
        error_msgs_aux += [new_value]

    ### Params - Info ###

    if isinstance(context_info, dict):
      params_info_dict = context_info.get('params')
      dynamic_params_info_dict = context_info.get(
          'dynamic_params'
      )

      dynamic_params_info = dict()

      for param_key in (dynamic_params_info_dict or dict()):
        if params_info_dict.get(param_key):
          error_msgs_aux += [[
              'context: duplicate param info key',
              'param_key: ' + param_key,
              'msg: duplicate param key '
              + '(defined both in params and dynamic_params)',
          ]]
        else:
          service_info = dynamic_params_info_dict.get(param_key)
          service_name = service_info
          service_param_name = param_key

          if isinstance(service_info, dict):
            service_name = service_info.get('name')
            service_param_name = service_info.get(
                'param'
            ) or param_key

          service_inner_data = services_data.get(service_name) or dict()
          service_data_params = service_inner_data.get(
              'params'
          ) or dict()
          param_value = service_data_params.get(
              service_param_name
          )

          if param_value is not None:
            dynamic_params_info[param_key] = param_value

      params_args = dict(
          params=merge_dicts(dynamic_params_info, params_info_dict),
          group_params=context_info.get('group_params'),
          shared_params=context_info.get('shared_params'),
          shared_group_params=context_info.get(
              'shared_group_params'
          ),
          shared_group_params_dict=shared_group_params_dict,
          shared_params_dict=shared_params_dict,
          group_params_dict=group_params_dict,
      )

      info = mix(params_args)

      result_aux_info = info.get('result')
      error_msgs_aux_info = info.get('error_msgs') or list()

      for value in (error_msgs_aux_info or []):
        new_value = ['context: service info params'] + value
        error_msgs_aux += [new_value]

    ### Params - Main ###

    dynamic_params = dict()

    for param_key in (dynamic_params_dict or dict()):
      if params_dict.get(param_key):
        error_msgs_aux += [[
            'context: duplicate param info key',
            'param_key: ' + param_key,
            'msg: duplicate param key '
            + '(defined both in params and dynamic_params)',
        ]]
      else:
        service_info = dynamic_params_dict.get(param_key)
        service_name = service_info
        service_param_name = param_key

        if isinstance(service_info, dict):
          service_name = service_info.get('name')
          service_param_name = service_info.get(
              'param'
          ) or param_key

        service_inner_data = services_data.get(service_name) or dict()
        service_data_params = service_inner_data.get(
            'params'
        ) or dict()
        param_value = service_data_params.get(
            service_param_name
        )

        if param_value is not None:
          dynamic_params[param_key] = param_value

    params_args = dict(
        params=merge_dicts(dynamic_params, params_dict),
        group_params=context_data.get('group_params'),
        shared_params=context_data.get('shared_params'),
        shared_group_params=context_data.get('shared_group_params'),
        shared_group_params_dict=shared_group_params_dict,
        shared_params_dict=shared_params_dict,
        group_params_dict=group_params_dict,
    )

    info = mix(params_args)

    result_aux = info.get('result')
    error_msgs_aux += info.get('error_msgs') or list()

    for value in error_msgs_aux:
      new_value = ['context: params'] + value
      error_msgs += [new_value]

    if not error_msgs:
      params = merge_dicts(result_aux, result_aux_info, result_aux_ctx_info)
      result['params'] = params or None

    return dict(result=result, error_msgs=error_msgs)
  except Exception as error:
    error_msgs += [[
        'msg: error when trying to prepare mixed params',
        'error type: ' + str(type(error)),
        'error details: ',
        traceback.format_exc().split('\n'),
    ]]
    return dict(error_msgs=error_msgs)


def prepare_mixed_loaded_contents(context_full_info, run_info):
  result = dict()
  error_msgs = []

  try:
    env_data = run_info.get('env_data')

    env = env_data.get('env')

    info = prepare_mixed_contents(context_full_info, run_info)

    result_aux = info.get('result')
    error_msgs = info.get('error_msgs') or list()

    if not error_msgs:
      contents = result_aux.get('contents')
      error_msgs_aux = list()

      validators = list()
      prepared_contents = dict()

      for content_key in sorted(list((contents or dict()).keys())):
        content = contents.get(content_key)

        info = load_content(content, env=env, run_info=run_info)

        prepared_content = info.get('result')
        meta = info.get('meta') or dict()
        validators = meta.get('validators') or []
        validators += validators
        error_msgs_aux_content = info.get('error_msgs') or list()

        for value in (error_msgs_aux_content or []):
          new_value = [str('content: ' + content_key)] + value
          error_msgs_aux += [new_value]

        if not error_msgs_aux_content:
          prepared_contents[content_key] = prepared_content

      for value in error_msgs_aux:
        new_value = ['context: load contents'] + value
        error_msgs += [new_value]

      if not error_msgs:
        result['contents'] = prepared_contents or None
        result['validators'] = validators or None

    return dict(result=result, error_msgs=error_msgs)
  except Exception as error:
    error_msgs += [[
        'msg: error when trying to prepare mixed loaded contents',
        'error type: ' + str(type(error)),
        'error details: ',
        traceback.format_exc().split('\n'),
    ]]
    return dict(error_msgs=error_msgs)


def prepare_mixed_contents(context_full_info, run_info):
  result = dict()
  error_msgs = []

  try:
    context_data = context_full_info.get('data')
    context_info = context_full_info.get('info')
    context_ctx_info = context_full_info.get('ctx_info')

    services_data = run_info.get('services_data')

    ### Contents ###

    result_aux_ctx_info = None
    result_aux_info = None
    error_msgs_aux = []

    contents_dict = context_data.get('contents')
    dynamic_contents_dict = context_data.get('dynamic_contents')

    ### Contents - Ctx Info ###

    if context_ctx_info:
      contents_ctx_info_dict = context_ctx_info.get('contents')
      dynamic_contents_ctx_info_dict = context_ctx_info.get(
          'dynamic_contents'
      )

      dynamic_contents_info = dict()

      for content_key in (dynamic_contents_ctx_info_dict or dict()):
        if contents_ctx_info_dict.get(content_key):
          error_msgs_aux += [[
              'context: duplicate content ctx info key',
              'content_key: ' + content_key,
              'msg: duplicate content key '
              + '(defined both in contents and dynamic_contents)',
          ]]
        else:
          service_info = dynamic_contents_ctx_info_dict.get(content_key)
          service_name = service_info
          service_content_name = content_key

          if isinstance(service_info, dict):
            service_name = service_info.get('name')
            service_content_name = service_info.get(
                'content'
            ) or content_key

          service_inner_data = services_data.get(service_name) or dict()
          service_data_contents = service_inner_data.get(
              'contents'
          ) or dict()
          content_value = service_data_contents.get(
              service_content_name
          )

          if content_value is not None:
            dynamic_contents_info[content_key] = dict(
                type='str',
                params=dict(value=content_value)
            )

      result_aux_ctx_info = merge_dicts(
          dynamic_contents_info, contents_ctx_info_dict)

    ### Contents - Info ###

    if isinstance(context_info, dict):
      contents_info_dict = context_info.get('contents')
      dynamic_contents_info_dict = context_info.get(
          'dynamic_contents'
      )

      dynamic_contents_info = dict()

      for content_key in (dynamic_contents_info_dict or dict()):
        if contents_info_dict.get('content_key'):
          error_msgs_aux += [[
              'context: duplicate content info key',
              'content_key: ' + content_key,
              'msg: duplicate content key '
              + '(defined both in contents and dynamic_contents)',
          ]]
        else:
          service_info = dynamic_contents_info_dict.get(content_key)
          service_name = service_info
          service_content_name = content_key

          if isinstance(service_info, dict):
            service_name = service_info.get('name')
            service_content_name = service_info.get(
                'content'
            ) or content_key

          service_inner_data = services_data.get(service_name) or dict()
          service_data_contents = service_inner_data.get(
              'contents'
          ) or dict()
          content_value = service_data_contents.get(
              service_content_name
          )

          if content_value is not None:
            dynamic_contents_info[content_key] = dict(
                type='str',
                params=dict(value=content_value)
            )

      result_aux_info = merge_dicts(dynamic_contents_info, contents_info_dict)

    ### Contents - Main ###

    dynamic_contents = dict()

    for content_key in (dynamic_contents_dict or dict()):
      if contents_dict.get(content_key):
        error_msgs_aux += [[
            'context: duplicate content info key',
            'content_key: ' + content_key,
            'msg: duplicate content key '
            + '(defined both in contents and dynamic_contents)',
        ]]
      else:
        service_info = dynamic_contents_dict.get(content_key)
        service_name = service_info
        service_content_name = content_key

        if isinstance(service_info, dict):
          service_name = service_info.get('name')
          service_content_name = service_info.get(
              'content'
          ) or content_key

        service_inner_data = services_data.get(service_name) or dict()
        service_data_contents = service_inner_data.get(
            'contents'
        ) or dict()
        content_value = service_data_contents.get(
            service_content_name
        )

        if content_value is not None:
          dynamic_contents[content_key] = dict(
              type='str',
              params=dict(value=content_value)
          )

    result_aux = merge_dicts(dynamic_contents, contents_dict)

    contents = merge_dicts(result_aux, result_aux_info, result_aux_ctx_info)

    for value in error_msgs_aux:
      new_value = ['context: contents'] + value
      error_msgs += [new_value]

    if not error_msgs:
      result['contents'] = contents or None

    return dict(result=result, error_msgs=error_msgs)
  except Exception as error:
    error_msgs += [[
        'msg: error when trying to prepare mixed contents',
        'error type: ' + str(type(error)),
        'error details: ',
        traceback.format_exc().split('\n'),
    ]]
    return dict(error_msgs=error_msgs)


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
    validators = prepared_content.get('validators')
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


def prepare_content(content, env, run_info, additional_info):
  error_msgs = list()

  try:
    if is_str(content):
      content = dict(
          type='str',
          params=dict(value=content)
      )

    additional_info = additional_info or dict()
    parent_content_info = additional_info.get('parent_content_info')

    params_dicts = dict(
        shared_group_params_dict=env.get(
            'content_shared_group_params'
        ),
        shared_params_dict=env.get('content_shared_params'),
        group_params_dict=env.get('content_group_params'),
    )

    context_full_info = dict(
        data=content,
        info=parent_content_info,
    )

    info = prepare_mixed_data(
        context_full_info, params_dicts, run_info
    )

    if not info.get('error_msgs'):
      mixed_content = info.get('result')
      mixed_content['type'] = content.get('type')
      mixed_content['name'] = content.get('name')
      mixed_content['key'] = content.get('key')
      mixed_content['origin'] = content.get('origin')
      mixed_content['file'] = content.get('file')
      mixed_content['schema'] = content.get('schema')
      mixed_content['validator'] = content.get('validator')

      mixed_content_keys = list(mixed_content.keys())

      for key in mixed_content_keys:
        if mixed_content.get(key) is None:
          mixed_content.pop(key, None)

      info = prepare_content_inner(
          content=mixed_content,
          env=env,
          run_info=run_info,
          additional_info=additional_info,
      )

    return info
  except Exception as error:
    error_msgs = [[
        'msg: error when trying to prepare the mixed content',
        'error type: ' + str(type(error)),
        'error details: ',
        traceback.format_exc().split('\n'),
    ]]
    return dict(error_msgs=error_msgs)


def prepare_content_inner(content, env, run_info, additional_info=None):
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
                  parent_content_info=content,
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

          if content_type in ['str', 'template']:
            result['params'] = content.get('params')

          if content_type == 'template':
            result['input'] = input_params or None
            result['credentials'] = content.get('credentials')
            result['contents'] = content.get('contents')

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
