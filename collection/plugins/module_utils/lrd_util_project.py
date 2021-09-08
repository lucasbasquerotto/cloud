#!/usr/bin/python

# (c) 2020, Lucas Basquerotto
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
#
# Used by the Cloud Preparation Step

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

import traceback

from ansible_collections.lrd.cloud.plugins.module_utils.lrd_utils import is_str, to_bool
from ansible_collections.lrd.cloud.plugins.module_utils.lrd_util_validation import (
    validate_ctx_schema
)


def prepare_ctx(ctx_name, env, env_init, env_original, env_info):
  error_msgs_ctx = list()
  result = dict()

  try:
    has_original_env = env_info.get('has_original_env')
    env_dir = env_info.get('env_dir')
    env_lax = env_info.get('env_lax')

    if not ctx_name:
      error_msgs_ctx += [['msg: context name not specified']]
    else:
      result['name'] = ctx_name

      main_dict = env.get('main')
      cloud_dict = env.get('cloud') or dict()

      if not main_dict:
        error_msgs_ctx += [['msg: main environment dictionary not specified']]
      elif ctx_name not in main_dict:
        error_msgs_ctx += [['msg: context not in the main environment dictionary']]
      else:
        ctx = main_dict.get(ctx_name)

        extend_cloud = to_bool(ctx.get('extend_cloud'))
        repo = ctx.get('repo')
        repo = repo if (repo is not None) else (
            cloud_dict.get('repo') if extend_cloud else None
        )
        result['repo'] = repo
        ext_repos = ctx.get('ext_repos')
        ext_repos = ext_repos if (ext_repos is not None) else (
            cloud_dict.get('ext_repos') if extend_cloud else None
        )
        result['ext_repos'] = ext_repos
        run_file = ctx.get('run_file')
        run_file = run_file if (run_file is not None) else (
            cloud_dict.get('run_file') if extend_cloud else None
        )
        run_file = run_file or 'run'
        result['run_file'] = run_file

        repos = env.get('repos')

        if not repo:
          error_msgs_ctx += [[
              'msg: cloud repository not defined for the context '
              + '(under the ' + ('main or cloud' if extend_cloud else 'main')
              + ' section) in the environment dictionary'
          ]]
        elif not repos:
          error_msgs_ctx += [['msg: no repositories in the environment dictionary']]
        elif not repos.get(repo):
          error_msgs_ctx += [[
              'context: validate ctx repo',
              'msg: repository not found: ' + repo,
          ]]

        for ext_repo in (ext_repos or []):
          ext_repo_name = ext_repo.get('repo')

          if not repos.get(ext_repo_name):
            error_msgs_ctx += [[
                'context: validate ctx env repo',
                str('msg: repository not found: ' + ext_repo_name),
            ]]

        collections = ctx.get('collections')
        collections = collections if (collections is not None) else (
            cloud_dict.get('collections') if extend_cloud else None
        )

        if collections:
          prepared_collections = list()
          collection_namespaces = set()
          collection_only_namespaces = set()
          collection_dests = set()

          for collection_idx, collection in enumerate(collections):
            error_msgs_collection = list()

            collection_namespace = collection.get('namespace')
            collection_name = collection.get('collection')
            collection_path = collection.get('path')

            collection_dest = collection_namespace

            if collection_name:
              collection_dest = collection_namespace + '/' + collection_name

            if ((collection_namespace == 'lrd') and (not collection_name)):
              error_msgs_collection += [[
                  'collection namespace: ' + str(collection_namespace),
                  'msg: reserved collection namespace (namespace only)',
              ]]
            elif ((collection_namespace == 'lrd') and (collection_name == 'cloud')):
              error_msgs_collection += [[
                  'collection namespace: ' + str(collection_namespace),
                  'collection name: ' + str(collection_name),
                  'msg: reserved collection',
              ]]
            elif collection_namespace in collection_only_namespaces:
              error_msgs_collection += [[
                  'collection namespace: ' + str(collection_namespace),
                  'msg: duplicate collection namespace '
                  + '(there is another collection with namespace only)',
              ]]
            elif (not collection_name) and collection_namespace in collection_namespaces:
              error_msgs_collection += [[
                  'collection namespace: ' + str(collection_namespace),
                  'msg: duplicate collection namespace (namespace only)',
              ]]
            elif collection_dest in collection_dests:
              error_msgs_collection += [[
                  'collection: ' + str(collection_dest),
                  'msg: duplicate collection',
              ]]

            if not collection_name:
              collection_only_namespaces.add(collection_namespace)

            if error_msgs_collection:
              for value in error_msgs_collection:
                new_value = [
                    str('collection item: #' + str(collection_idx + 1))
                ] + value
                error_msgs_ctx += [new_value]
            else:
              collection_namespaces.add(collection_namespace)
              collection_dests.add(collection_dest)

              default_mode = 777 if env_lax else 755
              prepared_collection = dict(
                  src=collection_path,
                  dest='ansible/collections/ansible_collections/' + collection_dest,
                  mode=collection.get('mode') or default_mode,
                  dir_mode=collection.get('dir_mode') or default_mode,
                  absent=to_bool(collection.get('absent')) or False,
              )
              prepared_collections += [prepared_collection]

          result['prepared_collections'] = prepared_collections

        ctl_env_schema = ctx.get('ctl_env_schema')
        original_env_schema = ctx.get('original_env_schema')
        nodes = ctx.get('nodes')

        if nodes:
          node_names = list()

          for node_idx, node in enumerate(nodes):
            error_msgs_node = list()

            node_name = node if is_str(node) else node.get('name')

            if not node_name:
              error_msgs_node += [[
                  'msg: node name not defined',
              ]]
            elif node_name in node_names:
              error_msgs_node += [[
                  'node name: ' + str(node_name),
                  'msg: duplicate node name',
              ]]

            if error_msgs_node:
              for value in error_msgs_node:
                new_value = [
                    str('node item: #' + str(node_idx + 1))
                ] + value
                error_msgs_ctx += [new_value]
            else:
              node_names += [node_name]

          result['node_names'] = node_names

        if has_original_env and ctl_env_schema:
          error_msgs_ctx += [[
              'ctl_env_schema: ' + str(ctl_env_schema),
              'msg: ctl_env_schema should not be defined the base environment file '
              + '(only in the original environment file)'
          ]]
        elif (not has_original_env) and original_env_schema:
          error_msgs_ctx += [[
              'original_env_schema: ' + str(original_env_schema),
              'msg: original_env_schema should not be defined the original environment file '
              + '(only in the base environment file)'
          ]]

        if (not has_original_env) and ctl_env_schema:
          task_data = dict(
              base_dir_prefix=env_dir + '/',
              dict_to_validate=env_init.get('env_params'),
              all_props=True,
          )

          info = validate_ctx_schema(
              ctx_title='validate the controller project environment params schema',
              schema_files=ctl_env_schema,
              task_data=task_data,
          )
          error_msgs_ctx += (info.get('error_msgs') or [])

        if has_original_env and original_env_schema:
          task_data = dict(
              base_dir_prefix=env_dir + '/',
              dict_to_validate=env_original,
              all_props=True,
          )

          info = validate_ctx_schema(
              ctx_title='validate the original environment schema',
              schema_files=original_env_schema,
              task_data=task_data,
          )
          error_msgs_ctx += (info.get('error_msgs') or [])
  except Exception as error:
    error_msgs_ctx += [[
        'ctx_name: ' + str(ctx_name or ''),
        'msg: error when trying to prepare the minimal context',
        'error type: ' + str(type(error)),
        'error details: ',
        traceback.format_exc().split('\n'),
    ]]

  error_msgs = list()

  for value in (error_msgs_ctx or []):
    new_value = [str('ctx: ' + str(ctx_name))] + value
    error_msgs += [new_value]

  return dict(result=result, error_msgs=error_msgs)


def prepare_project(env, env_init, env_original, env_info):
  result = dict()
  error_msgs = list()

  try:
    env_info = env_info or dict()
    has_original_env = env_info.get('has_original_env')
    env_dir = env_info.get('env_dir')

    if not env_init:
      error_msgs += [['msg: initial environment dictionary not specified']]

    if has_original_env and not env_original:
      error_msgs += [[
          'msg: original environment dictionary not specified '
          + '(when used with a base repository)'
      ]]

    if not env_dir:
      error_msgs += [['msg: environment repository directory not specified']]

    if not env:
      error_msgs += [['msg: environment dictionary not specified']]

    if not error_msgs:
      env_name = env.get('name')
      result['name'] = env_name

      if not env_name:
        error_msgs += [['msg: the environment does not have a name']]

      migration = env.get('migration') or ''
      container = env.get('container') or ''

      init_migration = env_init.get('migration') or ''
      init_container = env_init.get('init').get('container') or ''

      if migration and not init_migration:
        error_msgs += [[
            'migration: ' + str(migration),
            'msg: the migration version is specified in project environment but is '
            + 'not specified in the controller (main environment file)',
        ]]
      elif migration and (migration != init_migration):
        error_msgs += [[
            'migration: ' + str(migration),
            'ctl migration: ' + str(init_migration),
            'msg: the migration version is specified in project environment but is '
            + 'different than the one specified in the controller '
            + '(main environment file)',
        ]]

      if container and not init_container:
        error_msgs += [[
            'container: ' + str(container),
            'msg: the container is specified in project environment but is '
            + 'not specified in the controller (main environment file)',
        ]]
      elif container and (container != init_container):
        error_msgs += [[
            'container: ' + str(container),
            'ctl container: ' + str(init_container),
            'msg: the container is specified in project environment but is '
            + 'different than the one specified in the controller '
            + '(main environment file)',
        ]]

      ctl_env_schema = env.get('ctl_env_schema')
      original_env_schema = env.get('original_env_schema')

      if has_original_env and ctl_env_schema:
        error_msgs += [[
            'ctl_env_schema: ' + str(ctl_env_schema),
            'msg: ctl_env_schema should not be defined the base environment file '
            + '(only in the original environment file)'
        ]]
      elif (not has_original_env) and original_env_schema:
        error_msgs += [[
            'original_env_schema: ' + str(original_env_schema),
            'msg: original_env_schema should not be defined the original environment file '
            + '(only in the base environment file)'
        ]]

      if has_original_env and original_env_schema:
        task_data = dict(
            base_dir_prefix=env_dir + '/',
            dict_to_validate=env_original,
            all_props=True,
        )

        info = validate_ctx_schema(
            ctx_title='validate the original environment schema',
            schema_files=original_env_schema,
            task_data=task_data,
        )
        error_msgs += (info.get('error_msgs') or [])

      task_data = dict(
          dict_to_validate=env,
          all_props=True,
      )

      info = validate_ctx_schema(
          ctx_title='validate the environment (minimum) schema',
          schema_files=['schemas/env_minimum.schema.yml'],
          task_data=task_data,
      )
      error_msgs += (info.get('error_msgs') or [])

      if not env.get('ctxs'):
        error_msgs += [['msg: no context name(s) specified for the project']]

    if not error_msgs:
      prepared_ctxs = list()
      ctx_names = list()

      for ctx_idx, ctx_name in enumerate(env.get('ctxs')):
        error_msgs_ctx = list()
        ctx_data = None

        if ctx_name and (ctx_name in ctx_names):
          error_msgs_ctx += [[
              'ctx name: ' + str(ctx_name or ''),
              'msg: duplicate context name',
          ]]
        else:
          info = prepare_ctx(
              ctx_name,
              env=env,
              env_init=env_init,
              env_original=env_original,
              env_info=env_info,
          )
          ctx_data = info.get('result')
          error_msgs_ctx += (info.get('error_msgs') or [])

        for value in (error_msgs_ctx or []):
          new_value = [str('ctx item: #' + str(ctx_idx + 1))] + value
          error_msgs += [new_value]

        if not error_msgs_ctx:
          ctx_names += [ctx_name]
          prepared_ctxs += [ctx_data]

      result['prepared_ctxs'] = prepared_ctxs

      env_params = env_init.get('env_params') or dict()
      default_ctx = env_params.get('default_ctx')
      default_node = env_params.get('default_node')

      if default_node and not default_ctx:
        error_msgs_ctx += [[
            'default node: ' + str(default_node or ''),
            'msg: the default node is defined, but not the default context',
        ]]

      if default_ctx and (default_ctx not in ctx_names):
        error_msgs_ctx += [[
            'default ctx: ' + str(default_ctx or ''),
            'msg: the default context is not present in the project contexts',
            'project contexts: ',
            ctx_names,
        ]]
      else:
        if default_ctx:
          default_ctx = [
              ctx
              for ctx in prepared_ctxs
              if (ctx.get('name') == default_ctx)
          ][0]
        elif (not default_ctx) and (len(prepared_ctxs) == 1):
          ctx = prepared_ctxs[0]
          default_ctx = ctx.get('name')
          node_names = ctx.get('node_names') or list()

        if default_ctx:
          if default_node and not node_names:
            error_msgs_ctx += [[
                'default ctx: ' + str(default_ctx or ''),
                'default node: ' + str(default_node or ''),
                'msg: the default context has no nodes',
            ]]
          elif default_node and (default_node not in node_names):
            error_msgs_ctx += [[
                'default ctx: ' + str(default_ctx or ''),
                'default node: ' + str(default_node or ''),
                'msg: the default node is not present in the context',
                'allowed nodes: ',
                node_names,
            ]]
          elif (not default_node) and (len(node_names) == 1):
            default_node = node_names[0]

      result['default_ctx'] = default_ctx
      result['default_node'] = default_node

    result_keys = list(result.keys())

    for key in result_keys:
      if result.get(key) is None:
        result.pop(key, None)

    return dict(result=result, error_msgs=error_msgs)
  except Exception as error:
    error_msgs += [[
        'msg: error when trying to prepare the minimal contexts',
        'error type: ' + str(type(error)),
        'error details: ',
        traceback.format_exc().split('\n'),
    ]]
    return dict(error_msgs=error_msgs)
