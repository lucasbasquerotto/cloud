#!/bin/bash

{% if (project_ssh_default_ctx | default('')) != '' %}
    {% if not (project_ssh_default_ctx in (project_ssh_ctxs | default([]))) %}
        {% set error = {} %}
        {{ error['error.invalid_ctx.' + project_ssh_default_ctx] }}
    {% endif %}
    {% set ssh_default_ctx = project_ssh_default_ctx %}
{% else %}
    {% if (project_ssh_ctxs | default([]) | length) == 1 %}
        {% set ssh_default_ctx = project_ssh_ctxs[0] %}
    {% endif %}
{% endif %}
{% if (project_ssh_default_node | default('')) != '' %}
    {% if not (project_ssh_default_node in (project_ssh_nodes | default([]))) %}
        {% set error = {} %}
        {{ error['error.invalid_node.' + project_ssh_default_node] }}
    {% endif %}
    {% set ssh_default_node = project_ssh_default_node %}
{% else %}
    {% if (project_ssh_nodes | default([]) | length) == 1 %}
        {% set ssh_default_node = project_ssh_nodes[0] %}
    {% endif %}
{% endif %}

export project_title={{ project_run_ctxs_title | quote }}
export project_ctxs={{ project_run_ctxs_list | default([]) | join(',') }}
export project_ctx_cloud_dir={{ project_run_ctx_cloud_dir | quote }}
export project_secrets_cloud_dir={{ project_secrets_cloud_dir | quote }}
export project_ssh_default_ctx={{ ssh_default_ctx | default('') | quote }}
export project_ssh_default_node={{ ssh_default_node | default('') | quote }}
