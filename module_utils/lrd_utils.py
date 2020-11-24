#!/usr/bin/python

# (c) 2020, Lucas Basquerotto
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# pylint: disable=missing-module-docstring
# pylint: disable=missing-function-docstring

from __future__ import absolute_import, division, print_function
__metaclass__ = type # pylint: disable=invalid-name

import yaml

try:
  from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
  from yaml import Loader, Dumper

def merge_dicts(*args):
  new_dict = None

  for current_dict in (args or []):
    if not new_dict:
      new_dict = current_dict.copy()
    else:
      new_dict.update(current_dict)

  return new_dict

def load_yaml(text):
  return yaml.load(text, Loader=Loader)

def load_yaml_file(file_path):
  with open(file_path, 'rb') as file:
    content = file.read().decode('utf-8-sig')
    return load_yaml(content)

def error_text(error_msgs):
  separator = "-------------------------------------------"
  new_error_msgs = [separator]

  for value in error_msgs:
    new_error_msgs += [value, separator]

  error = yaml.dump(new_error_msgs, Dumper=Dumper, default_flow_style=False)

  return error
