#!/usr/bin/python

# (c) 2020, Lucas Basquerotto
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# pylint: disable=missing-module-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=import-error
# pylint: disable=broad-except

from __future__ import absolute_import, division, print_function
__metaclass__ = type  # pylint: disable=invalid-name

import traceback

from ansible_collections.lrd.cloud.plugins.module_utils.lrd_utils import merge_dicts


def expand_group_params(group_params, group_params_dict, ctx_name=None):
  result = dict()
  error_msgs = list()

  try:
    ctx_info = (' (' + ctx_name + ')') if ctx_name else ''

    if group_params:
      for key in sorted(list(group_params.keys())):
        mapped_key = group_params.get(key)

        if mapped_key:
          if (not group_params_dict) or (mapped_key not in group_params_dict):
            error_msgs += [[
                str('group_params key: ' + key + ctx_info),
                str('group_params mapped_key: ' + mapped_key),
                'group_params_dict keys:',
                sorted(
                    str(dict_key)
                    for dict_key in list(group_params_dict.keys())
                ) if group_params_dict else '',
                'msg: group_params mapped key not present in dict',
            ]]
          else:
            result[key] = group_params_dict.get(mapped_key)

    return dict(result=result, error_msgs=error_msgs)
  except Exception as error:
    error_msgs += [[
        'msg: error when trying to expand group params',
        'error type: ' + str(type(error)),
        'error details: ',
        traceback.format_exc().split('\n'),
    ]]
    return dict(error_msgs=error_msgs)


def mix_inner(args):
  result = dict()
  error_msgs = list()

  try:
    params = args.get('params')
    group_params = args.get('group_params')
    shared_params = args.get('shared_params')
    shared_group_params = args.get('shared_group_params')
    shared_group_params_dict = args.get('shared_group_params_dict')
    shared_params_dict = args.get('shared_params_dict')
    group_params_dict = args.get('group_params_dict')

    group_params_expanded = dict()

    if group_params:
      info = expand_group_params(group_params, group_params_dict)
      result_aux = info.get('result')
      error_msgs_aux = info.get('error_msgs') or list()

      if error_msgs_aux:
        error_msgs += error_msgs_aux
      else:
        group_params_expanded = result_aux

    shared_params_expanded = dict()

    if shared_params:
      for key in shared_params:
        if (not shared_params_dict) or (key not in shared_params_dict):
          error_msgs += [[
              str('shared_params key: ' + key),
              'shared_params_dict keys',
              sorted(
                  str(dict_key)
                  for dict_key in list(shared_params_dict.keys())
              ) if shared_params_dict else '',
              'msg: shared_params key not present in dict',
          ]]
        else:
          params_aux = shared_params_dict.get(key)
          shared_params_expanded = merge_dicts(
              shared_params_expanded, params_aux)

    shared_group_params_expanded = dict()

    if shared_group_params:
      shared_group_params_aux = dict()

      if (not shared_group_params_dict) or (shared_group_params not in shared_group_params_dict):
        error_msgs += [[
            str('shared_group_params: ' + shared_group_params),
            'shared_group_params_dict keys',
            sorted(
                str(dict_key)
                for dict_key in list(shared_group_params_dict.keys())
            ) if shared_group_params_dict else '',
            'msg: shared_group_params key not present in dict',
        ]]
      else:
        shared_group_params_aux = shared_group_params_dict.get(
            shared_group_params)

      if shared_group_params_aux:
        info = expand_group_params(
            shared_group_params_aux, group_params_dict, 'shared_group_params')
        result_aux = info.get('result')
        error_msgs_aux = info.get('error_msgs') or list()

        if error_msgs_aux:
          error_msgs += error_msgs_aux
        else:
          shared_group_params_expanded = result_aux

    if not error_msgs:
      if shared_group_params_expanded:
        result = merge_dicts(result, shared_group_params_expanded)

      if shared_params_expanded:
        result = merge_dicts(result, shared_params_expanded)

      if group_params_expanded:
        result = merge_dicts(result, group_params_expanded)

      if params:
        result = merge_dicts(result, params)

    return dict(result=result, error_msgs=error_msgs)
  except Exception as error:
    error_msgs += [[
        'msg: error when trying to mix parameters (inner)',
        'error type: ' + str(type(error)),
        'error details: ',
        traceback.format_exc().split('\n'),
    ]]
    return dict(error_msgs=error_msgs)


def mix(args):
  info = mix_inner(args)

  error_msgs = info.get('error_msgs') or list()

  if error_msgs:
    msg = str(len(error_msgs)) + ' error(s) when mixing parameters'
    error_msgs = [[msg]] + error_msgs + [[msg]]
    info['error_msgs'] = error_msgs

  return info
