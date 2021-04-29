FROM lucasbasquerotto/ctl:20210429

RUN apt-get update \
 && apt-get install -y --no-install-recommends git openssh-client \
 && rm -rf /var/lib/apt/lists/*

COPY container/run.sh /usr/local/bin/run
COPY container/ansible /usr/main/ansible

COPY collection /usr/main/ansible/collections/ansible_collections/lrd/cloud
COPY ansible/ansible.cfg /usr/main/ansible/ansible.cfg
COPY ansible/prepare.hosts /usr/main/ansible/hosts

COPY schemas /usr/main/ansible/schemas
COPY tasks/util /usr/main/ansible/tasks/util

RUN echo 'exec "${@}"' > /usr/local/bin/sudo \
 && chmod +x /usr/local/bin/sudo

CMD /usr/local/bin/run