#!/usr/bin/python

# (c) 2020, Lucas Basquerotto
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# pylint: disable=missing-module-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=wrong-import-position
# pylint: disable=import-error

from __future__ import absolute_import, division, print_function

from ansible_collections.lrd.cloud.plugins.module_utils.lrd_utils import error_text
from ansible_collections.lrd.cloud.plugins.module_utils.lrd_util_params_mixer import mix

from ansible.module_utils._text import to_text
from ansible.module_utils.basic import AnsibleModule

__metaclass__ = type  # pylint: disable=invalid-name

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}


DOCUMENTATION = '''
---
module: lrd_params_mixer
short_description: Mix parameters to create a resulting parameter dictionary.
description:
   - Mix parameters to create a resulting parameter dictionary.
version_added: "2.8"
options:
  params:
    description:
      - main parameters (overrides every other parameter)
    type: dict
  group_params:
    description:
      - group parameters (expands according to the values at group_params_dict)
    type: dict
  shared_params:
    description:
      - list with keys to map to shared_params_dict
    type: list
  shared_group_params:
    description:
      - key to shared_group_params_dict
    type: str
  shared_group_params_dict:
    description:
      - group parameters mapped from the key at shared_group_params
    type: dict
  shared_params_dict:
    description:
      - expanded parameters mapped from shared_params
    type: dict
  group_params_dict:
    description:
      - expanded parameters mapped from group_params and shared_group_params_dict
    type: dict
notes:
   - You can any of those parameters or none (but some parameters require others).

author: "Lucas Basquerotto (@lucasbasquerotto)"
'''


# ===========================================
# Module execution.
#


def main():
  module = AnsibleModule(
      argument_spec=dict(
          params=dict(type='dict'),
          group_params=dict(type='dict'),
          shared_params=dict(type='list'),
          shared_group_params=dict(type='str'),
          shared_group_params_dict=dict(type='dict'),
          shared_params_dict=dict(type='dict'),
          group_params_dict=dict(type='dict'),
      )
  )

  params_args = dict(
      params=module.params['params'],
      group_params=module.params['group_params'],
      shared_params=module.params['shared_params'],
      shared_group_params=module.params['shared_group_params'],
      shared_group_params_dict=module.params['shared_group_params_dict'],
      shared_params_dict=module.params['shared_params_dict'],
      group_params_dict=module.params['group_params_dict'],
  )

  info = mix(params_args)

  result = info.get('result')
  error_msgs = info.get('error_msgs')

  if error_msgs:
    module.fail_json(msg=to_text(error_text(error_msgs)))

  module.exit_json(changed=False, data=result)


if __name__ == '__main__':
  main()
