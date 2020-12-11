# Copyright: (c) 2012, Michael DeHaan <michael.dehaan@gmail.com>
# Copyright: (c) 2012-17, Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# pylint: disable=missing-module-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=wrong-import-position
# pylint: disable=import-error
# pylint: disable=protected-access

from __future__ import (absolute_import, division, print_function)

from ansible_collections.lrd.cloud.plugins.module_utils.lrd_utils import error_text
from ansible_collections.lrd.cloud.plugins.module_utils.lrd_util_pod_vars import load_vars

from ansible.module_utils._text import to_text
from ansible.plugins.lookup import LookupBase
from ansible.errors import AnsibleError

__metaclass__ = type  # pylint: disable=invalid-name

DOCUMENTATION = """
    name: lrd.cloud.content
    author: Lucas Basquerotto
    version_added: "2.11"
    short_description: retrieve contents of pod context after templating with Jinja2
    description:
      - Returns a dictionary with a list of directories, another list of files and another list of templates.
    options:
      _terms:
        description: contents to be loaded
        version_added: '2.11'
        type: list
      env_data:
        description: Data about the environment.
        version_added: '2.11'
        type: dict
      env:
        description: The environment dictionary or some other dictionary that may have the content group and shared parameters.
        default: env_data.env
        version_added: '2.11'
        type: dict
"""

RETURN = """
_raw:
   description: content loaded from the source specified
   type: dicts
   elements: raw
"""


class LookupModule(LookupBase):

  def run(self, terms, variables, **kwargs):
    env_data = kwargs.get('env_data')
    dependencies_data = kwargs.get(
        'dependencies_data',
        dict(list=list(), node_ip_dict=dict(), node_ips_dict=dict())
    )
    validate = kwargs.get('validate')
    ret = []
    error_msgs = []

    for term in terms:
      info = dict(
          plugin=self,
          ansible_vars=variables,
          env_data=env_data,
          dependencies_data=dependencies_data,
          validate=validate,
      )

      result_info = load_vars(
          pod=term,
          info=info,
      )

      result_aux = result_info.get('result')
      error_msgs_aux = result_info.get('error_msgs')

      if error_msgs_aux:
        error_msgs += error_msgs_aux
      else:
        ret.append(result_aux)

    if error_msgs:
      raise AnsibleError(to_text(error_text(error_msgs, 'pod_vars')))

    return ret
