#!/usr/bin/python

# (c) 2020, Lucas Basquerotto
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# pylint: disable=missing-module-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=wrong-import-position
# pylint: disable=import-error

from __future__ import absolute_import, division, print_function
__metaclass__ = type # pylint: disable=invalid-name

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}


DOCUMENTATION = '''
---
module: lrd_ctx
short_description: Return the context variables from the environment.
description:
   - Return the context variables from the environment.
version_added: "2.8"
options:
  ctx_name:
    description:
      - the context name
    type: str
    required: true
  env_data:
    description:
      - the environment data (vars, env type, ctx dir)
    type: dict
    required: true
    suboptions:
      env:
        description:
          - the environment dictionary.
        type: dict
        required: true
      env_dir:
        description:
          - specifies the path to the environment directory
        type: str
        required: true
      ctx_name:
        description:
          - the context name
        type: str
        required: true
      ctx_dir:
        description:
          - specifies the context directory
        type: str
        required: true
      dev:
        description:
          - specifies if it's a development environment
        type: bool
        required: true
      lax:
        description:
          - specifies if created files and directories will have less strict permissions
        type: bool
        required: true
      dev_repos_dir:
        description:
          - specifies the shared directory used during development
        type: str
        required: true
      dev_extra_repos_dir:
        description:
          - specifies the directory used for the extra repositories
        type: str
        required: true
      commit:
        description:
          - the current commit of the environment repository
        type: str
        required: true
      path_map:
        description:
          - the environment dictionary.
        type: dict
        required: true
  validate:
    description:
      - specifies if the schemas should be validated
    type: bool
    default: true
notes:
   - You can any of those parameters or none (but some parameters require others).

author: "Lucas Basquerotto (@lucasbasquerotto)"
'''

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_text
from ansible.module_utils.lrd_utils import error_text
from ansible.module_utils.lrd_util_ctx import prepare_ctx

# ===========================================
# Module execution.
#

env_data_spec = dict(
    env=dict(type='dict', required=True),
    env_dir=dict(type='str', required=True),
    ctx_name=dict(type='str', required=True),
    ctx_dir=dict(type='str', required=True),
    dev=dict(type='bool', required=True),
    lax=dict(type='bool', required=True),
    dev_repos_dir=dict(type='str', required=True),
    dev_extra_repos_dir=dict(type='str', required=True),
    commit=dict(type='str', required=True),
    path_map=dict(type='dict', required=True),
)

def main():
  module = AnsibleModule(
      argument_spec=dict(
          ctx_name=dict(type='str', required=True),
          env_data=dict(type='dict', required=True, options=env_data_spec),
          validate=dict(type='bool', default=True),
      )
  )

  ctx_name = module.params['ctx_name']
  env_data = module.params['env_data']
  validate_ctx = module.boolean(module.params['validate'])

  info = prepare_ctx(ctx_name, env_data, validate_ctx)

  result = info.get('result')
  error_msgs = info.get('error_msgs')

  if error_msgs:
    context = "ctx validation"
    module.fail_json(msg=to_text(error_text(error_msgs, context)))

  module.exit_json(changed=False, data=result)


if __name__ == '__main__':
  main()
