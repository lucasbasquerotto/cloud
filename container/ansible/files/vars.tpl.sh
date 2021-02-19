#!/bin/bash
export project_title={{ project_vars_title | quote }}
export project_ctxs={{ project_vars_ctxs | default([]) | join(',') | quote }}
export project_files_cloud_dir={{ project_vars_files_cloud_dir | quote }}
export project_secrets_cloud_dir={{ project_vars_secrets_cloud_dir | quote }}
export project_default_ctx={{ project_vars_default_ctx | quote }}
export project_default_node={{ project_vars_default_node | quote }}
