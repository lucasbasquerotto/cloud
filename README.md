# (Under Construction) Cloud Layer

This repository corresponds to the cloud layer and is used to deploy projects. This layer is responsible to deploy a specific project, using the [Cloud Input Vars](#cloud-input-vars) as the input values that contain the data needed to [deploy the project](#deploying-a-project).

_It's recommended to use a controller layer, like defined at http://github.com/lucasbasquerotto/ctl, to manage projects and generate those variables, instead of using this layer to deploy a project directly._

## Demo

Before start using this layer, it's easier to see it in action. Below is a simple demo used to deploy a project. The demo uses pre-defined [input variables](#cloud-input-vars), and then execute this layer to deploy a project.

To execute the demo you will need a container engine (like `docker` or `podman`).

1. Create an empty directory somewhere in your filesystem, let's say, `/var/demo`.

2. Create 2 directories in it: `env` and `data` (the names could be different, just remember to use these directories when mapping volumes to the container).

3. Create a `demo.yml` file inside `env` with the data needed to deploy the project:

```yaml
# Enter the data here (see the demo examples)
```

4. Deploy the project:

```shell
docker run -it --rm -v /var/demo/env:/env -v /var/demo/data:/lrd local/demo
```

**The above commands in a shell script:**

```shell
mkdir -p /var/demo/env /var/demo/data

cat <<'SHELL' > /var/demo/env/demo.yml
# Enter the data here (see the demo examples)
SHELL

docker run -it --rm -v /var/demo/env:/env -v /var/demo/data:/lrd local/demo
```

**That's it. The project was deployed.**

🚀 You can see examples of project deployment demos [here](#TODO).

The demos are great for what they are meant to be: demos, prototypes. **They shouldn't be used for development** (bad DX if you need real time changes without having to push and pull newer versions of repositories, furthermore you are unable to clone repositories in specific locations defined by you in the project folder). **They also shouldn't be used in production environments** due to bad security (the vault value used for decryption is `123456`, and changes to the [project environment repository](#project-environment) may be lost if you forget to push them).

# Table of Contents

- [Deploying a Project](#deploying-a-project)

  - [Project Base Directory](#project-base-directory)

  - [Cloud Input Vars](#cloud-input-vars)

  - [Cloud Preparation Step](#cloud-preparation-step)

  - [Cloud Context Input Vars](#cloud-context-input-vars)

  - [Cloud Context Preparation Step](#cloud-context-preparation-step)

  - [Cloud Context Main Step](#cloud-context-main-step)

    - [Main Step - Load Environment](#main-step---load-environment)

    - [Main Step - Initial Services](#main-step---initial-services)

    - [Main Step - Nodes - Create](#main-step---nodes---create)

    - [Main Step - Nodes - Wait for the hosts to be ready](#main-step---nodes---wait-for-the-hosts-to-be-ready)

    - [Main Step - Nodes - Prepare](#main-step---nodes---prepare)

    - [Main Step - Prepare the Pods](#main-step---prepare-the-pods)

    - [Main Step - Run Stages](#main-step---run-stages)

    - [Main Step - Nodes - Define the cron jobs](#main-step---nodes---define-the-cron-jobs)

    - [Main Step - Nodes - Finish](#main-step---nodes---finish)

    - [Main Step - Final Services](#main-step---final-services)

    - [Main Step - Delete Temporary Cloud Instances](#main-step---delete-temporary-cloud-instances)

    - [Main Step - Delete everything that was created previously](#main-step---delete-everything-that-was-created-previously)

- [Project Environment](#project-environment)

  - [Project Environment File](#project-environment-file)

  - [Project Environment Base File](#project-environment-base-file)

- [Useful Information](#useful-information)

  - [Cloud Next Parameters](#cloud-next-parameters)

  - [Mergeable Parameters](#mergeable-parameters)

  - [Credentials](#credentials)

  - [Contents](#contents)

    - [Content Type](#content-type)

    - [Content Origin](#content-origin)

    - [Transfer Content](#transfer-content)

    - [Content Full Example](#content-full-example)

  - [Schemas](#schemas)

  - [Extra Repositories](#extra-repositories)

  - [Pod Context](#pod-context)

    - [Pod Context Example](#pod-context-example)

    - [Pod Context Example Notes](#pod-context-example-notes)

  - [Services](#services)

  - [Run Stages](#run-stages)

  - [Encrypt and Decrypt](#encrypt-and-decrypt)


# Deploying a Project

The deployment of a project in this layer is done, by default, in 3 steps.

1. [Cloud Preparation Step](#cloud-preparation-step)

2. [Cloud Context Preparation Step](#cloud-context-preparation-step)

3. [Cloud Context Main Step](#cloud-context-main-step)

## Project Base Directory

The project base directory is the directory (`project_base_dir`) in which the files generated by the project deployment and used to deploy the project are located. The `project_base_dir` should be in the path `<base_path>/projects/<project_name>/` where `<base_path>` is a base folder for the relative paths of repositories defined in `path_params` (used in development).

When running with the `dev` [input variable](#cloud-input-vars) equal `true`, there should be a relative symlink `<project_base_dir>/dev/link` that points to `<base_path>` to map repositories (so that you can share repositories across projects).

When running this step in a container, `<project_base_dir>/dev` should map to `<base_path>` in the host, and a symlink `<base_path>/link` should be created pointing to itself (`.`) so that the relative symlinks work both inside and outside the container.

_If using the controller layer at http://github.com/lucasbasquerotto/ctl to deploy the project, the project base directory will be at `<root_dir>/projects/<project_name>/` and the symlinks and volume mappings will be already handled._

## Cloud Input Vars

The [Cloud Preparation Step](#cloud-preparation-step) needs a file in the following format located at `<project_base_dir>/files/ctl/vars.yml` to deploy a project:

```yaml
ctxs: []
dev: 'true'
env_params:
  env_dir: common
init:
  allow_container_type: false
  container: lucasbasquerotto/cloud:1.4.9
  container_type: docker
  root: true
  run_file: /usr/local/bin/run
key: demo
lax: true
migration: ''
path_params:
  path_env: repos/env
project_dir_relpath: projects/demo
repo:
  env_file: common/demo.yml
  src: https://github.com/lucasbasquerotto/env-base.git
  ssh_file: ''
  version: master
repo_vault:
  file: ''
  force: false
```

_(The values above are the output after running `./run launch --dev demo` with the `vars.yml` in the main environment repository being the same as [this example](http://github.com/lucasbasquerotto/ctl#main-environment-vars-file---example).)_

| Option | Description |
| ------ | ----------- |
| <nobr>`ctxs`</nobr> | Array with the contexts defined for the project. |
| <nobr>`dev`</nobr> | Boolean (or string equivalent) to specify if the project will run in development mode. |
| <nobr>`env_params`</nobr> | Object with the parameters specified in the `vars.yml` file in the [main environment repository](http://github.com/lucasbasquerotto/ctl#main-environment-repository). The parameters used will depend on the project and can be accessed in the [project environment file](#project-environment-file). |
| <nobr>`init.allow_container_type`</nobr> | Boolean (or string equivalent) to specify if the container engine that will deploy the project is to be allowed even if it's not one of the supported engines (docker and podman). |
| <nobr>`init.container`</nobr> | The container image that will deploy the project. |
| <nobr>`init.container_type`</nobr> | The container engine that will run the container that will deploy the project. |
| <nobr>`init.root`</nobr> | Boolean (or string equivalent) to specify if the container should be run as root. |
| <nobr>`init.run_file`</nobr> | Path to the file inside the container that will serve as an entrypoint to deploy the project. |
| <nobr>`key`</nobr> | Unique identifier of the project. |
| <nobr>`lax`</nobr> | Indicates if files and directories created and copied during the deployment will have less strict permissions (when `true`, recommended when in development). |
| <nobr>`migration`</nobr> | This will set the `migration` variable to be used to compare with the `migration` variable defined in the [project environment file](#project-environment-file), throwing an error in the preparation step, when the later value is defined and is different than the first `migration` variable. |
| <nobr>`path_params.path_env`</nobr> | When specified, is the directory, relative to the project root directory, in which the [project environment repository](#project-environment-repository) will cloned when in development mode. |
| <nobr>`path_params.path_env_base`</nobr> | When specified, is the directory, relative to the project root directory, in which the [project environment base repository](#project-environment-base-file) will cloned when in development mode. |
| <nobr>`path_params.path_map_repos`</nobr> | Dictionary of directories in which each key represents a repository as defined in the `repos` section in the [project environment file](#project-environment-file), and the value is the directory, relative to the project root directory, in which the repository will cloned when in development mode. |
| <nobr>`project_dir_relpath`</nobr> | Path, relative to the [controller root directory](http://github.com/lucasbasquerotto/ctl#root-directory), in which the artifacts created by this project are located. **This indicates where the project directory is located.**. |
| <nobr>`repo.env_file`</nobr> | The location of the [project environment file](#project-environment-file), inside the project environment repository. |
| <nobr>`repo.src`</nobr> | The source of the [project environment repository](#project-environment-repository). |
| <nobr>`repo.ssh_file`</nobr> | When specified (non empty), is the path in which the ssh key file to be used to clone the repository (when private) is located (the original path is relative to the [main environment repository](http://github.com/lucasbasquerotto/ctl#main-environment-repository), but at this point the original file was already copied, and possibly decrypted, to a path inside the project directory, `project_base_dir`). |
| <nobr>`repo.version`</nobr> | The version (branch/tag) of the [project environment repository](#project-environment-repository). |
| <nobr>`repo_vault.file`</nobr> | Path to the vault file with the pass to decrypt the project encrypted values. |
| <nobr>`repo_vault.force`</nobr> | Boolean (or string equivalent) to specify if the vault pass will be prompted if a vault file is not specified (when there isn't a vault file (`repo_vault.file` is empty), and `repo_vault.force` is `false`, the project mustn't have encrypted values, or an error will be thrown, when trying to decrypt them). |

## Cloud Preparation Step

This step receives a `project-dir` parameter with the [project base directory](#project-base-directory), then use the [Cloud Input Vars](#cloud-input-vars) at `<project_base_dir>/files/ctl/vars.yml` to load the [Project Environment](#project-environment), and, finally, for each context defined in the input vars (`ctxs`), clone the cloud repository for that context, as well as the repositories that will act as extensions (`env_repos`) for the cloud repository for the given context.

This preparation step is commonly executted inside a container, runs only once for the project and is the same even if the cloud repositories for the contexts are different, so it's expected that all the contexts in a project are compatible with this preparation step, and any specific stuff related to the context is run in the [Cloud Context Preparation Step](#cloud-context-preparation-step).

When loading the environment variables defined in the [`env_file`](#project-environment-file), if `repo_vault.file` is defined, the vault file there is used to [decrypt the encrypted values](#encrypt-and-decrypt). The [`env_file`](#project-environment-file) can access use jinja2 expressions and has access to the following variables:

- `project_name` (`string`): the project name, the value of `key` in the [Cloud Input Vars](#cloud-input-vars).
- `project_ctxs` (`list` of `string`): the contexts that will run in the project, the value of `ctxs` in the [Cloud Input Vars](#cloud-input-vars). The value `ctxs` is optional in the [Cloud Input Vars](#cloud-input-vars), and if not defined there, should be defined in the `env_file` (or `env_base_file`)
- `params` (`dict`): any parameters defined at `env_params` in the [Cloud Input Vars](#cloud-input-vars).

Aside from `project-dir`, the file that [runs this preparation step](container/run.sh) also accepts the following options:

| Option        | Description |
| ------------- | ----------- |
| <nobr>`-f`</nobr><br><nobr>`--force`</nobr> | Force the execution even if the commit of the [project environment repository](#project-environment) is the same as the last time it was executed. |
| <nobr>`-n`</nobr><br><nobr>`--next`</nobr> | The deployment will use parameters passed after the project name to be used by the next steps. The parameters are specified at the [Cloud Next Parameters](#cloud-next-parameters) section._ |
| <nobr>`-p`</nobr><br><nobr>`--prepare`</nobr> | Only runs the [Cloud Preparation Step](#cloud-preparation-step) and [Cloud Context Preparation Step](#cloud-context-preparation-step).<br><br>This has a particular feature that allows to pass arguments to each step that will handle it (as long as subsequent layers handle it). For example, passing the args `-vv` would generally be used only by the last step ([Cloud Context Main Step](#cloud-context-main-step)), but in this case it will be used as args to run the [Cloud Preparation Step](#cloud-preparation-step) and no args to subsequent steps.<br><br>You can pass `--` to indicate the end of the arguments for a given step, so the following args `-a -b -c -- -d` will pass the argument `-a -b -c` to the [Cloud Preparation Step](#cloud-preparation-step), and `-d` to the [Cloud Context Preparation Step](#cloud-context-preparation-step). You can use `--skip` to skip a given step (you shouldn't pass `--` in this case). For example, `--skip -c -d` will skip the [Cloud Preparation Step](#cloud-preparation-step) and pass `-c -d` to the [Cloud Context Preparation Step](#cloud-context-preparation-step). |
| <nobr>`-s`</nobr><br><nobr>`--fast`</nobr> | Skips the [Cloud Preparation Step](#cloud-preparation-step) and [Cloud Context Preparation Step](#cloud-context-preparation-step). |
| <nobr>`--debug`</nobr> | Runs in verbose mode and forwards this option to the subsequent step. |

In this step, when the `dev` input var is `true`, the `path_params` value in the [Cloud Input Vars](#cloud-input-vars) file will be included in a new file at `<project_base_dir>/files/cloud/path-map.yml` so that the next steps can use it to map repositories to other locations and skip pulling already cloned repositories.

The value of `env_params` is written to the file `<project_base_dir>/files/cloud/env-params.yml` so that the next steps can use it to load the [`env_file`](#project-environment-file).

For each context in the project, 2 files with the same content in a different format will be created at `<project_base_dir>/files/cloud/ctxs/<ctx>/vars.yml` and `<project_base_dir>/files/cloud/ctxs/<ctx>/vars.sh` to be used in the [Cloud Context Preparation Step](#cloud-context-preparation-step) and [Cloud Context Main Step](#cloud-context-main-step). The contents of those files are defined in the [Cloud Context Input Vars](#cloud-context-input-vars) section.

This steps generate a file `<project_base_dir>/files/cloud/run-ctxs` to run each context passing as the first parameter the location of context directory (`<project_base_dir>/files/cloud/ctxs/<ctx>/`). Each context is run entirely ([Cloud Context Preparation Step](#cloud-context-preparation-step) and [Cloud Context Main Step](#cloud-context-main-step)) before starting the next context.

## Cloud Context Input Vars

These are the input variables used by the [Cloud Context Preparation Step](#cloud-context-preparation-step) and [Cloud Context Main Step](#cloud-context-main-step). They are generated by the [Cloud Preparation Step](#cloud-preparation-step). There are 2 files generated with the same content, but in a different format:

_`<project_base_dir>/files/cloud/ctxs/<ctx>/vars.sh`_

```shell
export commit=24c74d6130bc3602388769aad14cbca8092a20b5
export ctx=demo
export ctx_dev_dir=/main/dev/link/projects/demo/files/cloud/ctxs/demo
export ctx_dir=/main/files/cloud/ctxs/demo
export dev_repos_dir=/main/dev/link
export env_dev=true
export env_dir=/main/dev/link/repos/env
export env_file=/main/dev/link/repos/env/common/demo.yml
export env_lax=true
export env_params_file=/main/files/cloud/env-params.yml
export path_map_file=/main/files/cloud/path-map.yml
export project=demo
export repo_dir=/main/files/cloud/ctxs/demo/repo
export repo_run_file=/main/files/cloud/ctxs/demo/repo/run
export secrets_cloud_dir=/main/secrets/cloud
export secrets_ctx_dir=/main/secrets/cloud/ctxs/demo
export vault_file=/main/secrets/ctl/vault
```

_`<project_base_dir>/files/cloud/ctxs/<ctx>/vars.yml`_

```yaml
commit: 24c74d6130bc3602388769aad14cbca8092a20b5
ctx: demo
ctx_dev_dir: /main/dev/link/projects/demo/files/cloud/ctxs/demo
ctx_dir: /main/files/cloud/ctxs/demo
dev_repos_dir: /main/dev/link
env_dev: 'true'
env_dir: /main/dev/link/repos/env
env_file: /main/dev/link/repos/env/common/demo.yml
env_lax: 'true'
env_params_file: /main/files/cloud/env-params.yml
path_map_file: /main/files/cloud/path-map.yml
project: demo
repo_dir: /main/files/cloud/ctxs/demo/repo
repo_run_file: /main/files/cloud/ctxs/demo/repo/run
secrets_cloud_dir: /main/secrets/cloud
secrets_ctx_dir: /main/secrets/cloud/ctxs/demo
vault_file: /main/secrets/ctl/vault
```

| Option | Description |
| ------ | ----------- |
| <nobr>`commit`</nobr> | The commit of the [project environment repository](#project-environment). |
| <nobr>`ctx`</nobr> | The environment context to be used in this step. |
| <nobr>`ctx_dev_dir`</nobr> | The context directory path inside the container using the path after `dev_repos_dir` when in development mode (mainly used to determine the relative paths between mapped repositories (`path_map_file`) and files and directories inside the context directory, `ctx_dir`). |
| <nobr>`ctx_dir`</nobr> | The context directory path inside the container. |
| <nobr>`dev_repos_dir`</nobr> | Path, inside the container, of the [controller root directory](http://github.com/lucasbasquerotto/ctl#root-directory) when in development mode. |
| <nobr>`env_dev`</nobr> | Boolean (or string equivalent) to specify if the project will run in development mode. |
| <nobr>`env_dir`</nobr> | The environment repository directory path inside the container. |
| <nobr>`env_file`</nobr> | The full path of the [project environment file](#project-environment-file), inside the container. |
| <nobr>`env_lax`</nobr> | Indicates if files and directories created and copied during the deployment will have less strict permissions (when `true`; recommended when in development). |
| <nobr>`env_params_file`</nobr> | Path, inside the container, of the `yaml` file that will have the value of `env_params` defined in the [Cloud Input Vars](#cloud-input-vars). |
| <nobr>`path_map_file`</nobr> | Path, inside the container, of the `yaml` file that will have the value of `path_params.path_map_repos` defined in the [Cloud Input Vars](#cloud-input-vars). |
| <nobr>`project`</nobr> | The project identifier, that has the value of `key` defined in the [Cloud Input Vars](#cloud-input-vars). |
| <nobr>`repo_dir`</nobr> | The cloud repository directory path inside the container. |
| <nobr>`repo_run_file`</nobr> | The file, inside the container, to run the cloud context steps ([Cloud Context Preparation Step](#cloud-context-preparation-step) and [Cloud Context Main Step](#cloud-context-main-step)).  |
| <nobr>`secrets_cloud_dir`</nobr> | The path, inside the container, of the directories with the secrets of the cloud layer. |
| <nobr>`secrets_ctx_dir`</nobr> | The path, inside the container, of the directories with the secrets of the current context in the cloud layer. |
| <nobr>`vault_file`</nobr> | Path, inside the container, to the vault file with the pass to decrypt the project encrypted values. |

The values of the files above are the output after running the [Cloud Preparation Step](#cloud-preparation-step) with the input variables in the [example](#cloud-input-vars) above.

## Cloud Context Preparation Step

This step as [defined in this repository](prepare.ctx.yml) does the following tasks:

1. Loads (from the environment repository) and validates the environment (`env`) variable [schema](#schemas) (as defined in the corresponding [schema file](schemas/env.schema.yml)).

2. Prepare the repositories defined in the `extra_repos` defined for the context in the environment file (`main.<ctx>.extra_repos`), which could be used, for example, to setup all the required repositories of a development environment to setup the workspace. It also clones the repositories of the pods defined for the nodes of the context (used when transfering templates of the pod to the actual pod repository in remote hosts, because Ansible requires that templates should be in the local machine, as well as some validations). This step doen't run when the `--prepare` and `--fast` flags are specified.

3. Defines and validates the context (`ctx_data`) variable, [merging and overriding parameters](#mergeable-parameters), defining the context ansible fact to be used for the next steps, so that those steps don't need to do it again. Validates [schemas](#schemas) for services, nodes, tasks and pods, and do several other types of validations, like ensuring the existence of some files that will be transfered.

4. Creates the hosts file to be used by Ansible when connecting to hosts (when new hosts are created dynamically, this file is updated) as well as the (optional) configuration file (`ansible.cfg`), that by default is the file [ansible/ansible.cfg](ansible/ansible.cfg), but can be overridden using the `cfg` property in the context object (in the environment file):

```yaml
# ...
main:
  my_context:
    repo: "cloud"
    cfg: |
      [defaults]
      interpreter_python=/usr/bin/python3
      stdout_callback = default
      collections_paths = collections
    hosts: |
      [main]
      localhost ansible_connection=local
      [host]
    # ...
  # ...
# ...
```

5. Creates the playbook to execute instructions in the hosts (from `files/run.tpl.yml` to `plays/run.yml`). This is needed because the instructions, and hosts to run the instructions, as well the order in which they are run, are dynamically defined in the project environment file, but Ansible expects that the playbook is already created and the hosts and plays to be statically defined when it starts to run the [Cloud Context Main Step](#cloud-context-main-step).

## Cloud Context Main Step

The main step of the cloud context is the actual deployment of the project. It consists of the following internal steps:

### Main Step - Load Environment

This step loads the environment file and defines and validates the context (`ctx_data`) variable, just like the steps 1 and 3 of the [Cloud Context Preparation Step](#cloud-context-preparation-step), except that it doesn't validate the schemas. These variables are used by the next steps in the local host (ansible group `main`).

### Main Step - Initial Services

This step create the initial services declared for the context in the environment file (in the property `initial_services`). For example, the code below would create the services `service_1`, `service_2` and `service_3` for the context `my_ctx`.

```yaml
# ...
main:
  my_ctx:
    repo: "cloud"
    # ...
    initial_services:
      - "service_1"
      - "service_2"
      - "service_3"
  # ...
# ...
services:
  service_1:
    #...
  service_2:
    #...
  service_3:
    #...
```

More information about services can be found [here](#services).

### Main Step - Nodes - Create

This step create the nodes declared for the context in the environment file. For example, the code below would create for the context `my_ctx`:

- 1 host according to the `node_1` specification;
- 1 host according to the `node_2` specification with the node type as `my_node_2` and named as `my-host`;
- 3 hosts according to the `node_3` specification.

```yaml
main:
  my_context:
    repo: "cloud"
    env_repos:
      - repo: "custom_cloud"
        dir: "custom-cloud"
    hosts:
      type: "template"
      file: "files/hosts.tpl.ini"
      schema: "files/hosts.schema.yml"
    nodes:
      - "node_1"
      - name: "my_node_2"
        key: "node_2"
        hostname: "my-host"
      - name: "node_3"
        amount: 3
nodes:
  node_1:
    service: "my_node_service"
    base_dir: "/var/cloud"
    credential: "host1"
    root: true
    shared_params: ["host_test"]
  node_2:
    service: "my_node_service"
    base_dir: "/var/cloud"
    credential: "host2"
    root: true
    shared_params: ["host_test"]
  node_3:
    service: "my_node_service"
    base_dir: "/var/cloud"
    credential: "host3"
    root: true
    shared_params: ["host_test"]
node_shared_params:
  host_test:
    setup_log_file: "/var/log/setup.log"
    setup_finished_log_regex: "^Setup Finished.*$"
    setup_success_log_last_line: "Setup Finished - Success"
    initial_connection_timeout: 90
    setup_finished_timeout: 300
services:
  my_node_service:
    #...
credentials:
  host1:
    host_user: "my-user1"
    host_pass: "p4$$w0rd1"
    ssh_file: "path/to/my-ssh-key-file1"
  host2:
    host_user: "my-user2"
    host_pass: "p4$$w0rd2"
    ssh_file: "path/to/my-ssh-key-file2"
  host3:
    host_user: "my-user3"
    host_pass: "p4$$w0rd3"
    ssh_file: "path/to/my-ssh-key-file3"
```

The example above would call the same [service](#services) to create the hosts, then it would include the hosts in the hosts file to be used by ansible. It would result in a hosts file like the following:

```ini
[main]
localhost ansible_connection=local

[host:children]
node_1
my_node_2
node_3

[node_1]
node-1-host ansible_host=<ip> ansible_user=my-user1 ansible_become_pass=p4$$w0rd1 ansible_ssh_private_key_file=<some_path>/path/to/my-ssh-key-file1 instance_type=node_1 instance_index=1 instance_public_ipv4=<ipv4> instance_public_ipv6=<ipv6> instance_private_ip=<private_ip>

[my_node_2]
my-host ansible_host=<ip> ansible_user=my-user2 ansible_become_pass=p4$$w0rd2 ansible_ssh_private_key_file=<some_path>/path/to/my-ssh-key-file2 instance_type=my_node_2 instance_index=1 instance_public_ipv4=<ipv4> instance_public_ipv6=<ipv6> instance_private_ip=<private_ip>

[node_3]
node-3-host ansible_host=<ip> ansible_user=my-user3 ansible_become_pass=p4$$w0rd3 ansible_ssh_private_key_file=<some_path>/path/to/my-ssh-key-file3 instance_type=node_3 instance_index=1 instance_public_ipv4=<ipv4> instance_public_ipv6=<ipv6> instance_private_ip=<private_ip>
node-3-host-2 ansible_host=<ip> ansible_user=my-user3 ansible_become_pass=p4$$w0rd3 ansible_ssh_private_key_file=<some_path>/path/to/my-ssh-key-file3 instance_type=node_3 instance_index=2 instance_public_ipv4=<ipv4> instance_public_ipv6=<ipv6> instance_private_ip=<private_ip>
node-3-host-3 ansible_host=<ip> ansible_user=my-user3 ansible_become_pass=p4$$w0rd3 ansible_ssh_private_key_file=<some_path>/path/to/my-ssh-key-file3 instance_type=node_3 instance_index=3 instance_public_ipv4=<ipv4> instance_public_ipv6=<ipv6> instance_private_ip=<private_ip>
```

The nodes accept a [dns_service](schemas/env.schema.yml) property (along with the `service` property) to define dns records for the created host if only one node replica (host) was created, according to the records defined in the property [dns_service_params_list](schemas/node.schema.yml).

These hosts will then be accessed in the next steps. More information about the services that can create nodes can be seen [here](#services).

### Main Step - Nodes - Wait for the hosts to be ready

This step waits for the created hosts (in the step [Nodes - Create](#main-step---nodes---create)) based on the information in the property [host_test](schemas/node.schema.yml) in the node:

- `initial_connection_timeout`: Timeout (in seconds) for the initial connection to the host.

- `setup_log_file`: Log file used to verify if the host setup was completed.

- `setup_finished_log_regex`: Regex applied to the log file used to determine if the setup ended.

- `setup_success_log_last_line`: Last line expected in the log file in the case of a successful setup.

- `setup_finished_timeout`: Timeout (in seconds) while waiting for the host setup to complete.

After connecting to the host, and verifying that the setup was successful, it then compares the environment repository commit with the commit registered in the previous deployment, to skip the deployment for the host if the commits are the same (see [Nodes - Wait for the hosts to be ready](#main-step---nodes---finish)).

You can force the deployment for the hosts even if the commit is the same, if the `force` flag was specified (explained at the [Cloud Preparation Step](#cloud-preparation-step)).

### Main Step - Nodes - Prepare

This step transfer the files defined in the `transfer` property in the node. The base directory for the contents to be transferred (when type is `custom`) is the cloud directory. More information about transferences of contents can be seen [here](#transfer-contents).

The destination will be the node directory, which is the workdir/chdir for the node tasks that run in the [run stages](#main-step---run-stages).

### Main Step - Prepare the Pods

This step transfer the files and templates referenced in the [pod context](#pod-context) file to the specified locations in the pod repository directory, possibly using the parameters, contents and credentials defined for the pod.

After transfering the files defined in the pod context, this step transfer the files defined in the `transfer` property in the pod. The base directory for the contents to be transferred (when type is `custom`), as well as the destination base directory, is the pod directory. More information about transferences of contents can be seen [here](#transfer-contents).

In this step, the transference of the files specified both in the pod context as well as in the pod `transfer` property go first to a temporary directory, and after that, to the real destinations. This is done mainly to avoid errors in the transference letting the pod directory in an inconsistent state. The tempoarary step can be skipped defining the pod property `fast_prepare` as `true` (recommended in development environments, for faster deployments).

### Main Step - Run Stages

TODO

- Run Stages

### Main Step - Nodes - Define the cron jobs

This step creates the cron files at the designated locations (defined in the [cron](schemas/node.schema.yml) property in the node), and then start the cron service if the property `cron_start` in the node is `true`.

### Main Step - Nodes - Finish

This step creates a file in the node with the environment repository commit, to skip newer deployments with the same commit (see [Main Step - Nodes - Wait for the hosts to be ready](#main-step---nodes---wait-for-the-hosts-to-be-ready)).

### Main Step - Final Services

This step is almost the same as the [Initial Services](#main-step---initial-services), except that it runs at the end of the deployment and is based on the property `final_services` (instead of `initial_services`).

### Main Step - Delete Temporary Cloud Instances

This step destroys/undeploys the nodes and services created/deployed in the previous steps, as long as they where defined with the property `tmp` as `true` (defaults to `false`).

_Example:_

```yaml
# ...
main:
  my_ctx:
    repo: "cloud"
    # ...
    initial_services:
      - name: "service_1"
        tmp: true
      - "service_2"
      - name: "service_3"
        tmp: true
      - name: "service_4"
    nodes:
      - name: "node_1"
        tmp: true
      - "node_2"
      - name: "node_3"
      - name: "node_4"
        tmp: true
    final_services:
      - name: "service_5"
        tmp: true
      - "service_6"
# ...
services:
  service_1:
    #...
  service_2:
    #...
  service_3:
    #...
  service_4:
    #...
  service_5:
    #...
  service_6:
    #...
nodes:
  node_1:
    #...
  node_2:
    #...
  node_3:
    #...
  node_4:
    #...
# ...
```

In the example above, the services `service_1`, `service_3` and `service_5` will be undeployed, and the nodes `node_1` and `node_4` will be destroyed (will be executed with the state property as `absent`). The `tmp` property shouldn't be defined in the service or node definition itself, but in the list of services or nodes in the context dictionary

### Main Step - Delete everything that was created previously

This step destroys/undeploys the nodes and services as long as they where defined with the property `can_destroy` as `true` (defaults to `false`). This property is defined in the same way as the `tmp` property is defined in the [previous step](#main-step---delete-temporary-cloud-instances).

**This step only runs if the [--end flag](#cloud-next-parameters) (or `--tags=destroy`) is passed during the launch.**

# Project Environment

The project environment is defined loading the [`env_file`](#project-environment-file) together with the params passed to it by the [Cloud Preparation Step](#cloud-preparation-step) (`project_name`, `project_ctxs` and `params`).

If the file has a top-level variable `env`, it will load the [`env_base_file`](#project-environment-base-file) passing the variables loaded from the [`env_file`](#project-environment-file) as params.

The loaded result from these files can be refered as being the **Project Environment**.

## Project Environment File

The project environment is defined loading the file defined in the variable `env_file` from the [Cloud Input Vars](#cloud-input-vars) together with the params passed to it by the [Cloud Preparation Step](#cloud-preparation-step) (`project_name`, `project_ctxs` and `params`).

This file should be inside the **project environment repository**, which should be cloned from `repo.src` with in the branch/tag `repo.version` specified in the [Cloud Input Vars](#cloud-input-vars). If `repo.ssh_file` is specified, the ssh file defined at `<project_base_dir>/secrets/ctl/` is used.

**Depending on the context, the project environment file may refer to the [Project Environment](#project-environment) itself.**

## Project Environment Base File

If the [`env_file`](#project-environment-file) has a top-level variable `env`, it will clone/pull the **project environment base repository** defined at `env.repo` in the directory `env.repo_dir` inside the project environment directory, then load the [`env_base_file`](#project-environment-base-file) defined at `env.file` relative to the project environment base repository, passing the variables loaded from the [`env_file`](#project-environment-file) as params.

It's not required for an [`env_file`](#project-environment-file) to have `env` specified in it to load variables from a base repository, but **this is very useful to share deployment variables between different environments (like staging and production)**, while keeping environment specific stuff, like endpoints, tokens, secrets, and other types of credentials in a separate directory.

_Example of an `env_file` that loads another file from a base repository:_

```yaml
name: "{{ project_name }}"
ctxs: "{{ project_ctxs }}"
env:
  repo:
    src: "https://github.com/lucasbasquerotto/project-env-base-demo.git"
    version: "master"
  repo_dir: "env-base"
  file: "common/repos.yml"
```

# Useful Information

## Cloud Next Parameters

The following are the parameters that can be specified when deploying a project with the `-n`/`--next` flag, specific to this layer:

| Option | Description |
| ------ | ------- |
| <nobr>`--end`</nobr> | Will destroy what was created by the deployment, the nodes and services, as long as the property `can_destroy` is defined and is `true` for them. It sends the state `absent` and expects that the nodes and services know how to handle this state. This is almost the same as running without the `--next` parameter as one of the launch parameters, and instead passing `--tags=destroy`, except that using `--end` won't register the commit of the project environment repository (used to skip newer deployments with the same commit, when not using the `--force` option) for this deployment (which is the expected behaviour, although in practice it probably won't matter). |
| <nobr>`--ssh`</nobr> | Will ssh into the host specified by the context (`-c`/`--ctx`), node type (`-n`/`--node`) and index (`-i`/`--idx`), with these params specified right after `--ssh`. When the context is not specified, if there is only one context in the deployment, this context will be used by default, otherwise an error will be thrown. When the node type is not specified, if there is only one node type in the context, this node type will be used by default, otherwise an error will be thrown. When the index is not specified, the default will be `1` (the first host of the previously mentioned node type). This ssh option can only be used after the preparation step is completed at least once, and the hosts are defined in the hosts file (either directly or after a node service creates them). |

_Example:_

```bash
# Connects through SSH if there's only 1 context in the project, and only 1 node in the context
./ctl/launch --next <project_name> --ssh

# Destroys the nodes and services
./ctl/launch --next <project_name> --end
```

## Mergeable Parameters

The environment file accepts some sections with `params`, `group_params`, `shared_params` and `shared_group_params` that can be merged and overridden. These parameters are merged in the step **#3** of the [Cloud Context Preparation Step](#cloud-context-preparation-step). **These mergeable parameters can be very useful to achieve a DRY approach, avoiding lots of duplication, but should be used moderately and with a good understanding of what it does, so as to not generate an illegible environment file with lots of indirections.**

The values specified in `params` will be considered as is.

```yaml
services:
  my_service:
    params:
      param1: 1
      param2: 2
```

_The above remains unchanged when the parameters are processed._

The values specified in `group_params` must be a dictionary in which the value of each property is a string that references a property in a group params dictionary that contains the values that will be mapped to the initial dictionary properties. The group params dictionary depends on the context that the `group_params` is specified (for example, if defined in a service, the group params dictionary is `service_group_params` defined at the topmost layer of the project environment variable; if defined in a node, will be `node_group_params`; and so on).

```yaml
services:
  my_service:
    group_params:
      param1: "group_1"
      param2: "group_2"
service_group_params:
  group_1: 3
  group_2: 4
```

_Is equivalent to:_

```yaml
services:
  my_service:
    params:
      param1: 3
      param2: 4
```

The values specified in `shared_params` must be an array of strings in which each string references a property in a shared params dictionary that contains the values that will be mapped to the whole parameter. The shared params dictionary depends on the context that the `shared_params` is specified (for example, if defined in a service, the shared params dictionary is `service_shared_params` defined at the topmost layer of the project environment variable; if defined in a node, will be `node_shared_params`; and so on).

The shared parameters are overridden in the order in which they are specified in the array, so the last one overrides all others, and the first is overridden by all others.

```yaml
services:
  my_service:
    shared_params: ["shared_1", "shared_2"]
service_shared_params:
  shared_1:
    param1: 11
    param2: 12
  shared_2:
    param2: 22
    param3: 23
```

_Is equivalent to:_

```yaml
services:
  my_service:
    params:
      param1: 11
      param2: 22
      param3: 23
```

The values specified in `shared_group_params` must be a string that references a property in a shared group params dictionary that contains the values that will expanded as group parameters, and then mapped to the whole parameter as a shared parameter. The shared group params dictionary depends on the context that the `shared_group_params` is specified (for example, if defined in a service, the shared params dictionary is `service_shared_group_params` defined at the topmost layer of the project environment variable; if defined in a node, will be `node_shared_group_params`; and so on).

The properties in the shared group params dictionary should behavle as `group_params`, so they must be dictionaries in which each property value is a string that map to the group params dictionary.

```yaml
services:
  my_service:
    shared_group_params: "shared_group_1"
service_shared_group_params:
  shared_group_1:
    param1: "group_shared_1"
    param2: "group_shared_2"
service_group_params:
  group_shared_1: 123
  group_shared_2: 456
```

_Is equivalent to:_

```yaml
services:
  my_service:
    params:
      param1: 123
      param2: 456
```

These sections are merged to result in a single parameter (`params`) property, with the precedence `shared_group_params` < `shared_params` < `group_params` < `params`, which means, for example, that what is defined in `params` will override the same parameter if specified in another section.

```yaml
services:
  my_service:
    params:
      param1: "value_1"
    group_params:
      param1: "group_1"
      param2: "group_2"
    shared_params: ["shared_1", "shared_2"]
    shared_group_params: "shared_group_1"
service_shared_group_params:
  shared_group_1:
    param1: "group_shared_1"
    param2: "group_shared_2"
    param3: "group_shared_3"
    param4: "group_shared_4"
    param5: "group_shared_5"
    param6: "group_shared_6"
service_shared_params:
  shared_1:
    param1: "value_shared_1_1"
    param2: "value_shared_1_2"
    param3: "value_shared_1_3"
    param4: "value_shared_1_4"
  shared_2:
    param4: "value_shared_2_4"
    param5: "value_shared_2_5"
service_group_params:
  group_1: "value_group_1"
  group_2: "value_group_2"
  group_shared_1: "value_group_shared_1"
  group_shared_2: "value_group_shared_2"
  group_shared_3: "value_group_shared_3"
  group_shared_4: "value_group_shared_4"
  group_shared_5: "value_group_shared_5"
  group_shared_6: "value_group_shared_6"
```

_Is equivalent to:_

```yaml
services:
  my_service:
    params:
      param1: "value_1"
      param2: "value_group_2"
      param3: "value_shared_1_3"
      param4: "value_shared_2_4"
      param5: "value_shared_2_5"
      param6: "value_group_shared_6"
```

Aside from merging the parameters defined in adjacent sections, the parameters can be overridden if the item that contains them are referenced in another place that allows to specify parameters for it. For example, when defining a list of services to be executed, instead of only the service name, mergeable parameters can also be defined for the service (as long as the service is not a list of services). The parameters defined here will have precedence over the parameters defined in the service directly:

```yaml
main:
  my_context:
    #...
    initial_services:
      - name: "my_service_01"
        key: "my_service"
        params:
          param1: "overridden_value_1_1"
        group_params:
          param1: "overridden_group_1_1"
          param2: "overridden_group_1_2"
      - name: "my_service_02"
        key: "my_service"
        params:
          param1: "overridden_value_2_1"
services:
  my_service:
    #...
    params:
      param1: "value_1"
    group_params:
      param1: "group_1"
      param2: "group_2"
service_group_params:
  group_1: "value_group_1"
  group_2: "value_group_2"
  overridden_group_1_1: "overridden_value_group_1_1"
  overridden_group_1_2: "overridden_value_group_1_2"
```

_Is equivalent to:_

```yaml
main:
  my_context:
    #...
    initial_services:
      - name: "my_service_01"
        key: "my_service"
        params:
          param1: "overridden_value_1_1"
          param2: "overridden_value_group_1_2"
      - name: "my_service_02"
        key: "my_service"
        params:
          param1: "overridden_value_2_1"
services:
  my_service:
    #...
    params:
      param1: "value_1"
      param2: "value_group_2"
```

_Which is also equivalent to:_

```yaml
main:
  my_context:
    #...
    initial_services: ["my_service_01", "my_service_02"]
services:
  my_service_01:
    #...
    params:
      param1: "overridden_value_1_1"
      param2: "overridden_value_group_1_2"
  my_service_02:
    #...
    params:
      param1: "overridden_value_2_1"
      param2: "value_group_2"
```

## Credentials

In general, credentials are used similarly to `group_params` as described at [mergeable parameters](#mergeable-parameters), in which you define a dictionary in which the value of each property is mapped to the property in the `credentials` section with that name. Like the mergeable parameters, they are mapped in the step **#3** of the [Cloud Context Preparation Step](#cloud-context-preparation-step).

_For example:_

```yaml
services:
  my_service:
    #...
    credentials:
      secret_01: "credential_01"
      secret_02: "credential_02"
credentials:
  credential_01:
    credential_01_param_01: "secret_value_01_01"
    credential_01_param_02: "secret_value_01_02"
  credential_02:
    credential_02_param_01: "secret_value_02_01"
    credential_02_param_02: "secret_value_02_02"
```

_Will turn into:_

```yaml
services:
  my_service:
    #...
    credentials:
      secret_01:
        credential_01_param_01: "secret_value_01_01"
        credential_01_param_02: "secret_value_01_02"
      secret_02:
        credential_02_param_01: "secret_value_02_01"
        credential_02_param_02: "secret_value_02_02"
```

One exception is the `nodes` section, in which it's not a dictionary `credentials` but a single `credential` string property that is mapped to a credentials in the `credentials` section:

```yaml
nodes:
  my_node:
    #...
    credential: "my_credential"
credentials:
  my_credential:
    credential_01: "secret_value_01"
    credential_02: "secret_value_02"
```

_Will turn into:_

```yaml
nodes:
  my_node:
    #...
    credential:
      credential_01: "secret_value_01"
      credential_02: "secret_value_02"
```

## Contents

When referring to `contents` here, the most common meaning is a string that can be huge, commonly stored in files, that can also be processed as templates (with jinja2), according to the parameters and credentials specified, as well as other internal contents that can be specified.

### Content Type

A content may be specified in different ways. It can be a string (`str`), a file, a (file) template or come from the `contents` section in the environment file, using the type `env`, and identifying with the `key` property (or the `name` property, if the `key` property is not specified).

_For example:_

Considering the following files:

_path/to/content/file.txt:_

```
I'm a content
This is a new line
```

_path/to/content/template.txt:_

```
I'm a {{ params.who_am_i }
This is a new line
```

Then the following cases are the same, only specified in different ways:

_Case 01:_

```yaml
services:
  my_service:
    #...
    contents:
      my_content:
        type: "str"
        params:
          value: |
            I'm a content
            This is a new line
```

_Case 02:_

```yaml
services:
  my_service:
    #...
    contents:
      my_content: |
        I'm a content
        This is a new line
```

(This is a short version of the previous case. When the type of the content is a string, it considers its type as `str`, and `params.value` as the string value.)

_Case 03:_

```yaml
services:
  my_service:
    #...
    contents:
      my_content:
        file: "path/to/content/file.txt"
```

(When the type of the content is a dictionary, it considers its type as `file`)

_Case 04:_

```yaml
services:
  my_service:
    #...
    contents:
      my_content:
        type: "template"
        file: "path/to/content/template.txt"
        params:
          who_am_i: "content"
```

_Case 05:_

```yaml
services:
  my_service:
    #...
    contents:
      my_content:
        name: "my_env_content"
        type: "env"
contents:
  my_env_content: |
    I'm a content
    This is a new line
```

### Content Origin

The contents may come from different places, when its type is `file` or `template`, according to the origin specified (`custom`, `env` or `cloud`).

- When `origin` is `env`, the file path is relative to the [project environment repository](#project-environment).
- When `origin` is `cloud`, the file path is relative to the cloud repository (specified in the main/context section, in the `repo` property).
- When `origin` is `custom` (default), the file path is relative do a path that depends on where it is used. For example, if specified in a pod, it will be relative to the pod repository; if specified in an [extra_repo](#cloud-context-preparation-step), it will be relative to that repository. When there isn't a specific path to be used, it's equivalent to `cloud` (for example, when used in a service or in a task at [run_stages](run-stages)).

### Transfer Content

Some sections in the environment file accepts a `transfer` property that is a list of objects whose source (`src`) is a [content](#contents) (will behave like the above), except that the content won't be loaded to a variable/fact. Instead, it will be transferred to the destination (`dest`) specified (with an optional `mode` property to define the permissions, an `executable` property to define that the file should be executable when `mode` is not defined, and a `when` property, that defaults to `true`, that will skip the transfer when it's `false`, which can also be used when overriding a transfer that has the same destination, to skip the transference, in sections that allow override transfers, that can be seen in the sub-schemas `main_node_info`, `main_pod_params_info` and `node_pod_info` in the [schema for the environment file](schemas/env.schema.yml)).

(#transfer-content).

The file permissions respects the following rules:

When the `lax` property is defined in the [Cloud Input Vars](#cloud-input-vars) or in the [Project Environment File](#project-environment-file) (the later having higher precedence than the previous) and has the value `true`, then:

- Directories will have the permission `777`.
- If the `executable` property is defined as `true`, files will have the permission `777`.
- If the `executable` property is defined as `false` (default), files will have the permission `666`.

Otherwise, when `lax` is `false` (default):

- Directories will have the permission `751`.
- If the `executable` property is defined as `true`, files will have the permission `751`.
- If the `executable` property is defined as `false` (default), files will have the permission `640`.

The `mode` property can be specified to define the file permissions explicitly (it has the highest precedence). Example:

```yaml
- dest: "path/to/dest/file.txt"
  src: |
    This is a string content
    This is a new line
  mode: "666"
```

The destination depends on where the `transfer` property is defined.

### Content Full Example

Considering that the [project environment repository](#project-environment) has the following files:

_path/to/content/file.txt:_

```
I'm a file content
This is a new line
```

_path/to/content/template.txt:_

```
I'm a template content
This is a new line

Value of params.param_01: {{ params.param_01 }}
Value of params.param_02: {{ params.param_02 }}

Value of credentials.secret_01: {{ credentials.secret_01 }}
Value of credentials.secret_02: {{ credentials.secret_02 }}

Value of contents.inner_content_01:
-----------------------------------
{{ contents.inner_content_01 }}
-----------------------------------

Value of contents.inner_content_02:
-----------------------------------
{{ contents.inner_content_02 }}
-----------------------------------
```

_path/to/content/template.inner.txt:_

```
I'm a template content inside another template content
This is a new line
Value of params.param_01: {{ params.param_01 }}
Value of params.param_02: {{ params.param_02 }}
```

Then the following:

```yaml
services:
  my_service:
    #...
    contents:
      content_str: |
        I'm a string content
        This is a new line
      content_file:
        origin: "env"
        file: "path/to/content/file.txt"
      content_template:
        type: "template"
        origin: "env"
        file: "path/to/content/template.txt"
        credentials:
          secret_01: "credential_01"
          secret_02: "credential_02"
        params:
          param_01: "value_01"
        group_params:
          param_01: "group_01"
          param_02: "group_02"
        contents:
          inner_content_01: "I'm a small string"
          inner_content_02:
            name: "my_inner_content_02"
            key: "my_content"
            type: "env"
            params:
              param_01: "overridden_value_01"
contents:
  my_content:
    content_template:
      type: "template"
      origin: "env"
      file: "path/to/content/template.inner.txt"
      params:
        param_01: "value_01"
        param_02: "value_02"
content_group_params:
  group_01: "value_group_01"
  group_02: "value_group_02"
credentials:
  credential_01: "secret_value_01"
  credential_02: "secret_value_02"
```

(You can see about `group_params` and overridable parameters in the section about [mergeable parameters](#mergeable-parameters).)

_Is equivalent to:_

```yaml
services:
  my_service:
    #...
    contents:
      content_str: |
        I'm a string content
        This is a new line
      content_file:
        origin: "env"
        file: "path/to/content/file.txt"
      content_template:
        type: "template"
        origin: "env"
        file: "path/to/content/template.txt"
        credentials:
          secret_01: "credential_01"
          secret_02: "credential_02"
        params:
          param_01: "value_01"
          param_02: "value_group_02"
        contents:
          inner_content_01: "I'm a small string"
          inner_content_02: |
            I'm a template content inside another template content
            This is a new line
            Value of params.param_01: overridden_value_01
            Value of params.param_02: value_02
credentials:
  credential_01: "secret_value_01"
  credential_02: "secret_value_02"
```

_Which is also equivalent to:_

```yaml
services:
  my_service:
    #...
    contents:
      content_str: |
        I'm a string content
        This is a new line
      content_file: |
        I'm a file content
        This is a new line
      content_template: |
        I'm a template content
        This is a new line

        Value of params.param_01: value_01
        Value of params.param_02: value_group_02

        Value of credentials.secret_01: secret_value_01
        Value of credentials.secret_02: secret_value_02

        Value of contents.inner_content_01:
        -----------------------------------
        I'm a small string
        -----------------------------------

        Value of contents.inner_content_02:
        -----------------------------------
        I'm a template content inside another template content
        This is a new line
        Value of params.param_01: overridden_value_01
        Value of params.param_02: value_02
        -----------------------------------
```

And can be accessed in the service task as `inner_service_contents.content_str`, `inner_service_contents.content_file` and `inner_service_contents.content_template`.

## Schemas

Schemas are defined to validate the structure of data that will be used in a given context. Most schema validations are done in the preparation steps ([Cloud Preparation Step](#cloud-preparation-step) and [Cloud Context Preparation Step](#cloud-context-preparation-step), specially in the later).

In most cases, schemas validate user defined data generated from [mergeable parameters](#mergeable-parameters), [credentials](#credentials), [contents](#contents), or a combination of them.

For example, if you try to specify `test: "my value"` in the top-most layer of the project environment file, you will receive an error saying that the property `test` is invalid, because the environment variable will be validated using the schema defined at [schemas/env.schema.yml](schemas/env.schema.yml).

The schema that validates the environment variable as a whole is fixed, but you can define custom schemas for specific cases, like services (when the service is not a list of services) and contents (when `type` is `template`). In the enviroment file, custom schemas are normally defined specifying the path to a custom schema file in a place that accepts a schema. Custom schemas are very useful because there are validations that depends on the environment, so they can't be known beforehand by the cloud layer.

_For example:_

Consider the following schema file:

_my/schema.yml_

```yaml
root: "my_schema"
schemas:
  my_schema:
    type: "dict"
    props:
      params:
        schema: "params"
        non_empty: true
  params:
    type: "dict"
    props:
      prop1:
        type: "str"
        non_empty: true
```

Then the following specification in the environment file:

```yaml
#...
main:
  my_context:
    #...
    initial_services:
      - "my_service_01"
      - "my_service_02"
      - "my_service_03"
      - "my_service_04"
      - "my_service_05"
      - "my_service_06"
services:
  my_service_01:
    #...
    schema: "my/schema.yml"
    params:
      prop1: "some value 01"
  my_service_02:
    #...
    schema: "my/schema.yml"
    params:
      prop1: "some value 01 - 02"
      prop2: "some value 02 - 02"
  my_service_03:
    #...
    schema: "my/schema.yml"
  my_service_04:
    #...
    schema: "my/schema.yml"
    params:
      prop1: ""
  my_service_05:
    #...
    schema: "my/schema.yml"
    params:
      prop1: "some value 05"
    contents:
      my_content: "content value"
  my_service_06:
    #...
    params:
      prop1: "some value 05"
    contents:
      my_content: "content value"
#...
```

Will have the following validation result:

- ✔️ The service `my_service_01` is validated successfully.
- ❌ The service `my_service_02` is validated unsuccessfully: `params.prop2` is present in the value being validated, but not specified in the schema.
- ❌ The service `my_service_03` is validated unsuccessfully: `params` is not present in the value being validated, but is required (`non_empty`) by the schema.
- ❌ The service `my_service_04` is validated unsuccessfully: `params.prop1` is empty in the value being validated, but the schema requires it to not be empty (`non_empty`).
- ❌ The service `my_service_05` is validated unsuccessfully: `contents` is present in the value being validated, but in the schema only `params` is present (when validating a service, for example, it is passed an object with its `params`, `credentials` and `contents`, but only when they are specified).
- ⚠️ The service `my_service_06` is not validated (it's advisable to validate with a custom schema in this case, although it's not required).

**Important:** Only sections used by the context are validated, so if `initial_services` was `["my_service_01", "my_service_06"]`, and the other services weren't used anywhere else in the context, there would be no errors.

Before validating the value, the schema itself is validated (because the schema may be wrong, for example, due to a typo). To validate the schemas, the schema at [schemas/schema.yml](schemas/schema.yml) is used. **You can take a look at it to familiarize yourself with schemas, as well as know what can be defined in a schema and their meanings.**

## Extra Repositories

The notation **extra repositories** is used to reference source control repositories that are cloned locally, defined in the `extra_repos` context property (in the main section).

One useful way to use them is to prepare a development environment, creating a project that maps the repositories that will be used in that environment to the paths in which you want them to be mapped.

_Here is a full example of an environment file:_

```yaml
name: "{{ params.name | default('repos') }}"
ctxs: ["repos_ctx"]
container: ""
main:
  repos_ctx:
    repo: "cloud"
    hosts: |
      [main]
      localhost ansible_connection=local
      [host]
    extra_repos:
      - repo: "env_base"
        dir: "env-base"
      - repo: "custom_cloud"
        dir: "custom-cloud"
      - repo: "pod"
        dir: "pod"
      - repo: "custom_pod"
        dir: "custom-pod"
      - repo: "app"
        dir: "app"
      - repo: "container_images"
        dir: "container-images"
      - repo: "backups"
        dir: "backups"
repos:
  env_base:
    src: "https://github.com/lucasbasquerotto/env-base.git"
    version: "master"
  cloud:
    src: "https://github.com/lucasbasquerotto/cloud.git"
    version: "master"
  custom_cloud:
    src: "https://github.com/lucasbasquerotto/custom-cloud.git"
    version: "master"
  pod:
    src: "https://github.com/lucasbasquerotto/pod.git"
    version: "master"
  custom_pod:
    src: "https://github.com/lucasbasquerotto/custom-pod.git"
    version: "master"
  app:
    src: "https://github.com/lucasbasquerotto/wordpress-docker.git"
    version: "master"
  container_images:
    src: "https://github.com/lucasbasquerotto/container-images.git"
    version: "master"
  backups:
    src: "https://github.com/lucasbasquerotto/backups.git"
    version: "master"
```

Then, in the `vars.yml` file in the main environment repository, add the project:

```yaml
#TODO add repos project definition
```

And run in development mode:

```shell
./ctl/launch -df repos
```

After that, the repositories specified in the `repos` section in the project environment file will be cloned in the paths specified in the `vars.yml` file (if some extra repository is not mapped in the `vars.yml` file, or if the project is deployed without the `-d`/`--dev` option, the repositories would be cloned in the directory for extra repositories for the project context, more specifically at `projects/repos/files/cloud/ctxs/repos_ctx/extra-repos/<extra_repo_dir>` in the controller root directory, although, in most cases, the extra repositories will probably be mapped to a specific directory).

Another use case for extra repositories is to reference repositories of the app layer in the pod layer when developing locally, so that you can map it to a pod container as a volume and execute a service with live changes, changing the code in the app repository, and seeing the changes without having to generate a new image.

_Sample (extra repos with app directory and docker-compose):_

_Project Environment File:_

```yaml
#...
main:
  my_context:
    #...
    extra_repos:
      - repo: "app_dir"
        dir: "app-dir"
pods:
  my_pod:
    repo: "pod"
    ctx: "path/to/ctx.yml"
    fast_prepare: true
    params:
      app_dir: "app-dir"
```

_path/to/ctx.yml ([pod context](#pod-context) file, in the pod repository):_

```yaml
{% set var_app_repo_dir = params.extra_repos_dir_relpath + '/' + params.main.app_dir %}

templates:

- src: "templates/docker-compose.env"
  dest: ".env"
  params:
    app_repo_dir: "{{ var_app_repo_dir }}"
```

(the parameter `extra_repos_dir_relpath` is always sent to the pod context)

_templates/docker-compose.env (in the pod repository):_

```yaml
APP_REPO_DIR={{ params.app_repo_dir }}
```

_docker-compose.yml (excerpt, in the pod repository):_

```yaml
services:
  my_service:
    image: "my_image"
    volumes:
      - "$APP_REPO_DIR:/path/inside/container"
```

## Pod Context

A pod context (not to be confounded with the environment/cloud context defined in the `main` section) defines files and templates to be copied to the pod repository, and also loads other pod sub-contexts that define more files and templates (and possibly more pod sub-contexts).

- A pod context is useful to avoid defining template parameters directly in the environment file and transfer with the `transfer` property; instead, the pod itself specifies the files that should be copied (this don't mean that the transfer option shouldn't be used, both can be used together).

- It can specify files from the environment repository that the pod know that are required (like a file with credentials) and move them to the pod repository.

- It's useful to avoid repetitions for different environments, because most things can be defined in the pod repository context file, and reused accross different environments, enjoying the benefit of jinja2 to parse the context file (that, in the end, is a jinja2 template) with powerful template features.

- It also avoids possible errors when defining files in wrong destinations in the environment file, or defining a file that is not used by the pod (thinking that it will be used).

- Each template to be transferred can have a schema defined to validate the parameters structure, so as to avoid wrong data passed to the template (these schemas reside in the pod, and the validation will be done for all environments that use the pod, so that you don't have to add an additional schema file for each environment).

- More than one item (file or template) to be transferred with the same destination will generate an error (to avoid possibly wrong configurations).

- The order in which the items will be transferred is not, necessarily, the order in which they were defined (in practice this won't matter, taking into account that they can't have the same destination)

The key items that can be defined in a pod context file are:

- `env_files`: list of files with paths relative to the environment directory, that will be copied to the specified destinations, relative to the pod directory.

- `env_templates`: list of template files with paths relative to the environment directory, that will be copied to the specified destinations, relative to the pod directory. The templates will be rendered with jinja2, using the variables passed in the `params` property.

- `files`: same as `env_files`, but the source paths (as well as the destination paths) are relative to the pod directory.

- `templates`: same as `env_templates`, but the source paths (as well as the destination paths) are relative to the pod directory.

- `children`: list of pod sub-contexts that will also be processed to define the files and templates to be transferred to the pod directory. The parameters that the sub-contexts can access should be provided by the parent context using the `params` property.

More details can be seen in the [pod context schema file](schemas/pod_ctx.schema.yml).

### Pod Context Example

Considering a project named `test-pod-local` with the following pod specification in the [project environment base file](#project-environment-base-file):

```yaml
#...
meta:
  lax: true
  template_no_empty_lines: true
main:
  pod_local:
    repo: "cloud"
    env_repos:
      - repo: "custom_cloud"
        dir: "custom-cloud"
    hosts: |
      [main]
      localhost ansible_connection=local
      [host]
    nodes:
      - name: "test_simple_node_local"
        key: "simple_local"
        local: true
nodes:
  simple_local:
    pods: ["simple"]
pods:
  simple:
    repo: "custom_pod"
    ctx: "test/ctx-simple.yml"
    schema: "test/simple.schema.yml"
    root: true
    fast_prepare: true
    params:
      env_files_dir: "{{ params.env.repo_dir }}/test/files"
      test_schema:
        - 123
        - { p1: [{ p1: [456, { p1: 111 }] }, 012, { p1: 123 }] }
        - 789
        - { p1: 000 }
      pod_param_1: "sample value 1"
      pod_param_2: "sample value 2"
      pod_param_3: "sample value 3"
repos:
  cloud:
    src: "https://github.com/lucasbasquerotto/cloud.git"
    version: "master"
  custom_cloud:
    src: "https://github.com/lucasbasquerotto/custom-cloud.git"
    version: "master"
  custom_pod:
    src: "https://github.com/lucasbasquerotto/custom-pod.git"
    version: "master"
```

_(In a **project environment base file**, you can reference the project environment base directory, inside the project environment directory, using `params.env.repo_dir`; so, the path to the test files directory (`env_files_dir`), in the example above, was specified as `{{ params.env.repo_dir }}/test/files`. If the file was the **project environment file** instead, then you could define the path as just `test/files`)_

And the following files:

_test/ctx-simple.yml (in the `custom_pod` repository):_

```yaml
{% set var_pod_kind = 'test' %}
{% set var_main_base_dir = params.main.custom_dir | default('') %}
{% set var_main_dir =
  (var_main_base_dir != '')
  | ternary(var_main_base_dir + '/', '')
  + var_pod_kind
%}

env_templates:

- src: "{{ params.main.env_files_dir }}/template.yml"
  dest: "env/env-template.yml"
  schema: "{{ params.main.env_files_dir }}/template.schema.yml"
  params:
    src: "{{ params.main.env_files_dir }}/template.yml"
    dest: "env/env-template.yml"
    schema: "{{ params.main.env_files_dir }}/template.schema.yml"
    params:
      prop1: 1
      prop2:
        prop2_1: "{{ params.main.pod_param_1 }}"
        prop2_2: "{{ params.main.pod_param_2 }}"

files:

- src: "{{ var_main_dir }}/pod-file.txt"
  dest: "env/file.main.txt"

templates:

- src: "{{ var_main_dir }}/dynamic.tpl.yml"
  dest: "env/pod-data.test.yml"
  params: {{ params | to_json }}

children:

- name: "{{ var_main_dir }}/ctx-child.yml"
  params:
    main: {{ params.main | to_json }}
    custom:
      value: "{{ params.main.pod_param_3 }}"
```

_test/ctx-child.yml (in the `custom_pod` repository):_

```yaml
{% set var_pod_kind = 'test' %}
{% set var_main_base_dir = params.main.custom_dir | default('') %}
{% set var_main_dir =
  (var_main_base_dir != '')
  | ternary(var_main_base_dir + '/', '')
  + var_pod_kind
%}

env_files:

- src: "{{ params.main.env_files_dir }}/file.txt"
  dest: "env/env-file.txt"

files:

- src: "{{ var_main_dir }}/pod-file.txt"
  dest: "env/file.child.txt"

- src: "{{ var_main_dir }}/pod-file.txt"
  dest: "env/file.child2.txt"

templates:

- src: "{{ var_main_dir }}/template.sh"
  dest: "env/script.sh"
  schema: "{{ var_main_dir }}/template.schema.yml"
  executable: true
  params:
    value: "{{ params.custom.value }}"
```

_test/simple.schema.yml (in the `custom_pod` repository):_

```yaml
root: "pod_schema"
schemas:
  pod_schema:
    type: "dict"
    props:
      params:
        schema: "params"
        non_empty: true
  params:
    type: "dict"
    props:
      env_files_dir:
        type: "str"
        non_empty: true
      custom_dir:
        type: "str"
      test_schema:
        non_empty: true
        schema: "test"
      pod_param_1:
        type: "str"
        non_empty: true
      pod_param_2:
        type: "str"
        non_empty: true
      pod_param_3:
        type: "str"
        non_empty: true
  test:
    type: "simple_list"
    elem_schema: "test2"
  test2:
    type: "simple_dict"
    alternative_type: "int"
    props:
      p1:
        type: "simple_map"
        elem_schema: "test"
```

_test/files/template.schema.yml (in the environment base repository)_

```yaml
root: "env_template_params"
schemas:
  env_template_params:
    type: "dict"
    props:
      src:
        required: true
        type: "str"
      dest:
        required: true
        type: "str"
      schema:
        type: "str"
      params:
        required: true
        type: "dict"
```

_test/template.schema.yml (in the `custom_pod` repository)_

```yaml
root: "pod_template_params"
schemas:
  pod_template_params:
    type: "dict"
    props:
      value:
        type: "str"
        non_empty: true
```

Then the deployment will create the following files (the destination is always is the `custom_pod` repository directory):

---

_`[src]` test/files/template.yml (in the environment base repository)_

```yaml
name: "test template"
src: "{{ params.src }}"
dest: "{{ params.dest }}"
{{ { 'params': params.params } | to_nice_yaml }}
```

_`[dest]` env/env-template.yml_

```yaml
name: "test template"
src: "env-base/test/files/template.yml"
dest: "env/env-template.yml"
params:
    prop1: 1
    prop2:
        prop2_1: sample value 1
        prop2_2: sample value 2
```

---

_`[src]` test/pod-file.txt (in the `custom_pod` repository)_

_`[dest]` env/file.main.txt_

(files keep the same content)

```
[Pod File Content]
New line
Last line
```

---

_`[src]` test/dynamic.tpl.yml (in the `custom_pod` repository)_

```yaml
{{ params | to_nice_yaml }}
```

_`[dest]` env/pod-data.test.yml_

```yaml
contents: {}
credentials: {}
ctx_name: pod_local
data_dir: ../../data/test-pod-local-pod_local-simple
dependencies_data:
    list: []
    node_ip_dict: {}
    node_ips_dict: {}
dev: true
env_name: test-pod-local
extra_repos_dir_relpath: ../../projects/test-pod-local/files/cloud/ctxs/pod_local/extra-repos
identifier: test-pod-local-pod_local-simple
lax: true
local: true
main:
    env_files_dir: env-base/test/files
    pod_param_1: sample value 1
    pod_param_2: sample value 2
    pod_param_3: sample value 3
    test_schema:
    - 123
    -   p1:
        -   p1:
            - 456
            -   p1: 111
        - 10
        -   p1: 123
    - 789
    -   p1: 0
pod_name: simple
```

---

_`[src]` test/files/file.txt (in the environment base repository)_

_`[dest]` env/env-file.txt_

(files keep the same content)

```
test file line 01
line 02
line 03
```

---

_`[src]` test/pod-file.txt (in the `custom_pod` repository)_

_`[dest]` env/file.child.txt_

_`[dest]` env/file.child2.txt_

(files keep the same content)

```
[Pod File Content]
New line
Last line
```

---

_`[src]` test/template.sh (in the `custom_pod` repository)_

```bash
#!/bin/bash

# shellcheck disable=SC1083
param_value={{ params.value | quote }}

# shellcheck disable=SC2154
echo "[template] param value = $param_value"
```

_`[dest]` env/script.sh_

```bash
#!/bin/bash
# shellcheck disable=SC1083
param_value='sample value 3'
# shellcheck disable=SC2154
echo "[template] param value = $param_value"
```

_(The lines were removed because the property `meta.template_no_empty_lines` in the environment file is `true`)_

---

### Pod Context Example Notes

**1. The pod data variable (`params`) accessed in the context file has the following properties:**

- `contents`: The pod contents (specified in the `contents` property). There is none in this example.
- `credentials`: The pod credentials (specified in the `credentials` property). There is none in this example.
- `ctx_name`: The context name (specified in the `main` section in the environment file). This is the name of the environment/cloud context, not the pod context.
- `data_dir`: The path of the pod data directory (for local pods, it's the relative path).
- `dependencies_data`: The node dependencies. There is none in this example.
- `dev`: When `true`, specifies that the deployment is in development mode.
- `env_name`: The environment name (specified in the `name` property in the environment file). In most cases, corresponds to the project name.
- `extra_repos_dir_relpath`: Relative path to the [extra-repos directory](#extra-repositories).
- `identifier`: The pod identifier, defined as `<env_name>-<ctx_name>-<pod_name>`, mainly used to avoid name collisions between different pods in the same host (especially when deploying locally).
- `lax`: Indicates if the permissions should be less strict (useful, for example, when defining the `mode` for files and templates).
- `local`: When `true`, means that the node in which the pod is being deployed is a local node (localhost).
- `main`: The pod parameters (specified in the `params` property). The name `main` was chosen mainly because the object that has all these properties (pod data) is called `params`, so you would call `params.main` instead of `params.params`.
- `pod_name`: The name of the pod.

The pod data variable (explained above and printed in the file `env/pod-data.test.yml` of the example) can only be accessed out-of-the-box in the context file. To access it in sub-context files, you have to pass it as a parameter. Example (passing as a `pod_data` parameter):

_test/ctx-simple.yml:_

```yaml
#...

children:

- name: "{{ var_main_dir }}/ctx-child.yml"
  params:
    pod_data: {{ params | to_json }}
    main: {{ params.main | to_json }}
    custom:
      value: "{{ params.main.pod_param_3 }}"
```

_test/ctx-child.yml:_

```yaml
#...

templates:

- src: "..."
  dest: "..."
  params: {{ params.pod_data | to_json }}
```

**2. Passing complex parameters:**

The pod context file is a template, so complex parameters may not be passed as intended to its items parameters (as templates and children), and even make the template as an invalid yaml file (causing errors when trying to load it). To avoid such problems, and taking into account that yaml is a superset of json, and that the filter `to_json` generates a one-line json, you can pass complex parameters, as well as multiline strings, as:

```yaml
#...

templates:

- src: "..."
  dest: "..."
  params: {{ my_complex_param | to_json }}
```

**3. File permissions:**

The file permissions respects the same rules defined in the section about [transference of contents](#transfer-content).

The `mode` property can be specified to define the file permissions explicitly (it has the highest precedence). Example:

```yaml
- src: "{{ var_main_dir }}/dynamic.tpl.yml"
  dest: "env/pod-data.test.yml"
  mode: "{{ params.lax | bool | ternary('666', '600') }}"
  params: {{ params | to_json }}
```

**4. Schemas:**

You can specify [schemas](#schemas) for your pod context templates, to validate their parameters.

In the example above there was the following `test_schema` parameter specified for the pod:

```yaml
#...
schema: "test/simple.schema.yml"
params:
  #...
  test_schema:
    - 123
    - { p1: [{ p1: [456, { p1: 111 }] }, 012, { p1: 123 }] }
    - 789
    - { p1: 000 }
  #...
```

And the following schema file:

_test/simple.schema.yml (in the `custom_pod` repository):_

```yaml
root: "pod_schema"
schemas:
  pod_schema:
    type: "dict"
    props:
      params:
        schema: "params"
        non_empty: true
  params:
    type: "dict"
    props:
      #...
      test_schema:
        non_empty: true
        schema: "test"
      #...
  test:
    type: "simple_list"
    elem_schema: "test2"
  test2:
    type: "simple_dict"
    alternative_type: "int"
    props:
      p1:
        type: "simple_map"
        elem_schema: "test"
```

This is a complex schema case that allows (possibly very) different values based on its type. More specifically, the `test` inner schema allows the value to be both a list of values or a single (entire) value that correspond to the `test2` inner schema specification, and this schema do a similar approach allowing the value to be either an integer value (end of the chain), or a dictionary with a `p1` property, that is itself either a single (entire) value or a dictionary of properties (with any name; a `map`) whose values correspond to the `test` inner schema specification (creating a recursion between the inner schemas).

This means that the following values are valid (accepted by the schema):

```yaml
test_schema: 111

test_schema: [222]

test_schema: { p1: 333 }

test_schema: [{ p1: 444 }, 555]

test_schema: { p1: { map_prop: 666 } }

test_schema:
  p1:
    map_prop_1:
      - 777
      - { p1: 888 }
    map_prop_2: 999

test_schema:
  - 123
  - { p1: [{ p1: [456, { p1: 111 }] }, 012, { p1: 123 }] }
  - 789
  - { p1: 000 }

# and so on...
```

But at the same time the schema will validate and throw errors for invalid values:

```yaml
test_schema: 'abc' # error

test_schema: [] # error

test_schema: {} # error

test_schema: { p2: 321 } # error

test_schema: [{ map_prop_outside_p1: 123 }] # error
```

This example is just a demonstration of the flexibility that can be achieved with schemas, it's not meant to be used in a real project.

## Services

#TODO

## Run Stages

```yaml
main:
  my_context:
    repo: "cloud"
    env_repos:
      - repo: "custom_cloud"
        dir: "custom-cloud"
    nodes:
      - "node_1"
      - name: "node_2"
        amount: 3
        max_amount: 5
    run_stages:
      - tasks:
          - name: "test_task_cloud"
            all_nodes: true
            node_task: true
            credentials:
              overridden: "test_task_overridden"
              run_stage: "test_task_run_stage"
            params:
              prop4: "overridden_cloud_1_4"
            shared_params: ["test_task_overridden_1"]
            contents:
              content_task_run_stage: |
                Content Tasks Cloud Run Stage
                Line 02
              content_task_overridden: |
                Content Tasks Cloud Overridden
                Line 02
          - name: "test"
            nodes:
              - name: "node_1"
                pods: ["pod_1"]
            pod_task: true
          - name: "test_skip"
            all_nodes: true
            node_task: true
      - tasks:
          - name: "test_task_env"
            nodes: ["node_1"]
            node_task: true
          - name: "test_task_pod"
            all_nodes: true
            pod_task: true
```

#TODO

## Encrypt and Decrypt

To encrypt and decrypt values and files, use `ansible-vault` as defined at http://github.com/lucasbasquerotto/ctl#encrypt-and-decrypt.
