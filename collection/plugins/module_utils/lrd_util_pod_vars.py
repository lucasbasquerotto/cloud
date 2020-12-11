#!/usr/bin/python

# (c) 2020, Lucas Basquerotto
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# pylint: disable=missing-module-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=import-error
# pylint: disable=broad-except

from __future__ import absolute_import, division, print_function
__metaclass__ = type  # pylint: disable=invalid-name

import os

from ansible_collections.lrd.cloud.plugins.module_utils.lrd_utils import load_yaml, to_bool
from ansible_collections.lrd.cloud.plugins.module_utils.lrd_util_template import lookup


def load_vars(pod_info, run_info, meta_info=None):
  pod = pod_info.get('pod')
  dependencies_data = pod_info.get(
      'dependencies_data',
      dict(list=list(), node_ip_dict=dict(), node_ips_dict=dict()),
  )

  plugin = run_info.get('plugin')
  ansible_vars = run_info.get('ansible_vars')
  env_data = run_info.get('env_data')
  validate = run_info.get('validate')

  meta_info = meta_info or dict()
  no_ctx_msg = meta_info.get('no_ctx_msg')

  result = None
  error_msgs = []

  pod_ctx_file = pod.get('ctx')

  params = dict(
      identifier=pod.get('identifier'),
      env_name=env_data.get('env').get('name'),
      ctx_name=env_data.get('ctx_name'),
      pod_name=pod.get('name'),
      local=pod.get('local'),
      main=pod.get('params', {}),
      credentials=pod.get('credentials', {}),
      data_dir=pod.get('data_dir'),
      extra_repos_dir_relpath=pod.get('extra_repos_dir_relpath'),
      dependencies_data=dependencies_data,
  )

  previous = dict(
      dir_names=set(),
      file_names=set(),
  )

  data_info = dict(
      plugin=plugin,
      ansible_vars=ansible_vars,
      env_data=env_data,
      pod=pod,
      previous=previous,
      validate=validate,
  )

  res = load_next_vars(
      file_relpath=pod_ctx_file,
      params=params,
      data_info=data_info,
  )

  error_msgs_aux = res.get('error_msgs')

  if error_msgs_aux:
    parent_type = pod.get('parent_type')
    parent_description = pod.get('parent_description')
    pod_description = pod.get('description')

    for value in error_msgs_aux:
      if no_ctx_msg:
        error_msgs += [value]
      else:
        new_value = [
            str(parent_type + ': ' + parent_description),
            str('pod: ' + pod_description),
        ] + value
        error_msgs += [new_value]
  else:
    result = res.get('result')

  return dict(result=result, error_msgs=error_msgs)


def load_next_vars(file_relpath, params, data_info):
  directories = list()
  files = list()
  templates = list()
  error_msgs = list()

  plugin = data_info.get('plugin')
  ansible_vars = data_info.get('ansible_vars')
  env_data = data_info.get('env_data')
  pod = data_info.get('pod')
  previous = data_info.get('previous')
  validate = data_info.get('validate')

  pod_dir = pod.get('pod_dir')
  pod_local_dir = pod.get('local_dir')
  pod_tmp_dir = pod.get('tmp_dir')

  dir_names = previous.get('dir_names')
  file_names = previous.get('file_names')

  env_lax = env_data.get('lax')
  default_dir_mode = 777 if env_lax else 751
  default_file_mode = 666 if env_lax else 640

  env_dir = env_data.get('env_dir')

  try:
    file = pod_dir + '/' + file_relpath

    if validate and not os.path.exists(file):
      error_msgs += [[
          str('file: ' + file_relpath),
          'msg: pod ctx file not found in the pod repository',
      ]]
      return dict(error_msgs=error_msgs)

    res_str = None

    try:
      res_str = lookup(plugin, ansible_vars, file, params)
    except Exception as error:
      error_msgs += [[
          str('file: ' + file_relpath),
          'msg: error when trying to load the pod ctx file',
          'error type: ' + str(type(error)),
          'error details: ' + str(error),
      ]]
      return dict(error_msgs=error_msgs)

    res = None

    try:
      res = load_yaml(str(res_str))
    except Exception as error:
      error_msgs += [[
          str('file: ' + file_relpath),
          'file content type: ' + str(type(res_str)),
          'msg: error when trying to process the pod ctx file',
          'error type: ' + str(type(error)),
          'error details: ' + str(error),
      ]]
      return dict(error_msgs=error_msgs)

    if res:
      res_files = res.get('files')
      res_templates = res.get('templates')
      res_env_files = res.get('env_files')
      res_env_templates = res.get('env_templates')

      for res_file in (res_files or []):
        when = res_file.get('when')

        if to_bool(when if (when is not None) else True):
          src_relpath = res_file.get('src')
          src = pod_dir + '/' + src_relpath
          local_src = pod_local_dir + '/' + src_relpath

          dest = pod_dir + '/' + res_file.get('dest')
          dest_dir = os.path.dirname(dest)

          if validate and not os.path.exists(local_src):
            error_msgs += [[
                str('src: ' + src_relpath),
                'msg: file not found in the pod repository',
            ]]

          if dest_dir not in dir_names:
            dir_names.add(dest_dir)
            dir_to_add = dict(
                path=dest_dir,
                mode=res_file.get('dir_mode') or default_dir_mode,
            )
            directories += [dir_to_add]

          if dest not in file_names:
            file_names.add(dest)
            file_to_add = dict(
                remote_src=True,
                src=src,
                dest=dest,
                mode=res_file.get('mode') or default_file_mode,
            )
            files += [file_to_add]
          else:
            error_msgs += [[
                str('src: ' + src),
                str('dest: ' + dest),
                'msg: duplicate destination for pod file',
            ]]

      for res_template in (res_templates or []):
        when = res_template.get('when')

        if to_bool(when if (when is not None) else True):
          src_relpath = res_template.get('src')
          src = pod_dir + '/' + src_relpath
          local_src = pod_local_dir + '/' + src_relpath

          dest_relpath = res_template.get('dest')
          dest = pod_dir + '/' + dest_relpath
          dest_tmp = pod_tmp_dir + '/tpl/' + dest_relpath

          dest_dir = os.path.dirname(dest)
          dest_tmp_dir = os.path.dirname(dest_tmp)

          if validate and not os.path.exists(local_src):
            error_msgs += [[
                str('src: ' + src_relpath),
                'msg: template file not found in the pod repository',
            ]]

          if dest_dir not in dir_names:
            dir_names.add(dest_dir)
            dir_to_add = dict(
                path=dest_dir,
                mode=res_template.get('dir_mode') or default_dir_mode,
            )
            directories += [dir_to_add]

          if dest_tmp_dir not in dir_names:
            dir_names.add(dest_tmp_dir)
            dir_to_add = dict(
                path=dest_tmp_dir,
                mode=res_template.get('dir_mode') or default_dir_mode,
            )
            directories += [dir_to_add]

          if dest not in file_names:
            file_names.add(dest)
            template_to_add = dict(
                src=src,
                dest=dest,
                dest_tmp=dest_tmp,
                mode=res_template.get('mode') or default_file_mode,
                params=res_template.get('params') or {},
            )
            templates += [template_to_add]
          else:
            error_msgs += [[
                str('src: ' + src),
                str('dest: ' + dest),
                'msg: duplicate destination for pod template',
            ]]

      for res_file in (res_env_files or []):
        when = res_file.get('when')

        if to_bool(when if (when is not None) else True):
          src_relpath = res_file.get('src')
          src = env_dir + '/' + src_relpath
          local_src = src

          dest = pod_dir + '/' + res_file.get('dest')
          dest_dir = os.path.dirname(dest)

          if validate and not os.path.exists(local_src):
            error_msgs += [[
                str('src: ' + src_relpath),
                'msg: file not found in the environment repository',
            ]]

          if dest_dir not in dir_names:
            dir_names.add(dest_dir)
            dir_to_add = dict(
                path=dest_dir,
                mode=res_file.get('dir_mode') or default_dir_mode,
            )
            directories += [dir_to_add]

          if dest not in file_names:
            file_names.add(dest)
            file_to_add = dict(
                src=src,
                dest=dest,
                mode=res_file.get('mode') or default_file_mode,
            )
            files += [file_to_add]
          else:
            error_msgs += [[
                str('src: ' + src),
                str('dest: ' + dest),
                'msg: duplicate destination for pod environment file',
            ]]

      for res_template in (res_env_templates or []):
        when = res_template.get('when')

        if to_bool(when if (when is not None) else True):
          src_relpath = res_template.get('src')
          src = env_dir + '/' + src_relpath
          local_src = src

          dest_relpath = res_template.get('dest')
          dest = pod_dir + '/' + dest_relpath
          dest_tmp = pod_tmp_dir + '/tpl/' + dest_relpath

          dest_dir = os.path.dirname(dest)
          dest_tmp_dir = os.path.dirname(dest_tmp)

          if validate and not os.path.exists(local_src):
            error_msgs += [[
                str('src: ' + src_relpath),
                'msg: template file not found in the environment repository',
            ]]

          if dest_dir not in dir_names:
            dir_names.add(dest_dir)
            dir_to_add = dict(
                path=dest_dir,
                mode=res_template.get('dir_mode') or default_dir_mode,
            )
            directories += [dir_to_add]

          if dest_tmp_dir not in dir_names:
            dir_names.add(dest_tmp_dir)
            dir_to_add = dict(
                path=dest_tmp_dir,
                mode=res_template.get('dir_mode') or default_dir_mode,
            )
            directories += [dir_to_add]

          if dest not in file_names:
            file_names.add(dest)
            template_to_add = dict(
                src=src,
                dest=dest,
                dest_tmp=dest_tmp,
                mode=res_template.get('mode') or default_file_mode,
                params=res_template.get('params') or {},
            )
            templates += [template_to_add]
          else:
            error_msgs += [[
                str('src: ' + src),
                str('dest: ' + dest),
                'msg: duplicate destination for pod environment template',
            ]]

      if not error_msgs:
        children = res.get('children')

        if children:
          for child in children:
            child_name = child.get('name')
            child_params = child.get('params')

            res_child = load_next_vars(
                file_relpath=child_name,
                params=child_params,
                data_info=data_info,
            )

            child_error_msgs = res_child.get('error_msgs')

            if child_error_msgs:
              for value in child_error_msgs:
                new_value = [str('ctx child: ' + child_name)] + value
                error_msgs += [new_value]
            else:
              res_child_result = res_child.get('result')

              child_directories = res_child_result.get('directories')
              child_files = res_child_result.get('files')
              child_templates = res_child_result.get('templates')

              if child_directories:
                directories += child_directories

              if child_files:
                files += child_files

              if child_templates:
                templates += child_templates
  except Exception as error:
    error_msgs += [[
        str('file: ' + file_relpath),
        'msg: error when trying to define the pod ctx vars',
        'error type: ' + str(type(error)),
        'error details: ' + str(error),
    ]]
    return dict(error_msgs=error_msgs)

  ret = dict(
      result=dict(
          directories=directories,
          files=files,
          templates=templates,
      ),
      error_msgs=error_msgs,
  )

  return ret
