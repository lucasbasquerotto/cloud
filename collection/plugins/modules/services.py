#!/usr/bin/python

# (c) 2020, Lucas Basquerotto
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# pylint: disable=missing-module-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=wrong-import-position
# pylint: disable=import-error

from __future__ import absolute_import, division, print_function

from ansible_collections.lrd.cloud.plugins.module_utils.lrd_util_ctx import prepare_services
from ansible_collections.lrd.cloud.plugins.module_utils.lrd_utils import error_text

from ansible.module_utils._text import to_text
from ansible.module_utils.basic import AnsibleModule

__metaclass__ = type  # pylint: disable=invalid-name

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}


DOCUMENTATION = '''
---
module: lrd.cloud.ctx
short_description: Return the context variables from the environment.
description:
   - Return the context variables from the environment.
version_added: "2.8"
options:
  services:
    description:
      - the services information
    type: list
    required: true
  env_data:
    description:
      - the environment data (vars, env type, ctx dir)
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

# ===========================================
# Module execution.
#


def main():
  module = AnsibleModule(
      argument_spec=dict(
          services=dict(type='list', required=True),
          env_data=dict(type='dict', required=True),
          validate=dict(type='bool', default=True),
      )
  )

  services = module.params['services']
  env_data = module.params['env_data']
  validate_ctx = module.boolean(module.params['validate'])

  info = prepare_services(services, env_data, validate_ctx, top=True)

  result = info.get('result')
  error_msgs = info.get('error_msgs')

  if error_msgs:
    module.fail_json(msg=to_text(error_text(error_msgs)))

  module.exit_json(changed=False, data=result)


if __name__ == '__main__':
  main()
