FROM lucasbasquerotto/ansible:0.0.2

RUN pip3 install pyyaml

COPY container/run.sh /usr/local/bin/run
COPY container/ansible /usr/main/ansible

COPY collection /usr/main/ansible/collections/ansible_collections/lrd/cloud
COPY ansible/callback_plugins /usr/main/ansible/callback_plugins
COPY ansible/ansible.cfg /usr/main/ansible/ansible.cfg
COPY ansible/prepare.hosts /usr/main/ansible/hosts

COPY schemas /usr/main/ansible/schemas
COPY tasks/util /usr/main/ansible/tasks/util

RUN echo 'exec "${@}"' > /usr/local/bin/sudo \
 && chmod +x /usr/local/bin/sudo

CMD /usr/local/bin/run