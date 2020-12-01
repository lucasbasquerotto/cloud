FROM lucasbasquerotto/ansible:0.0.2

RUN pip3 install pyyaml

COPY container/run.sh /usr/local/bin/run
COPY container/ansible /usr/main/ansible

COPY callback_plugins /usr/main/ansible/callback_plugins
COPY library /usr/main/ansible/library
COPY module_utils /usr/main/ansible/module_utils
COPY filter_plugins /usr/main/ansible/filter_plugins

COPY schemas /usr/main/ansible/schemas
COPY tasks/util /usr/main/ansible/tasks/util

RUN echo 'exec "${@}"' > /usr/local/bin/sudo \
 && chmod +x /usr/local/bin/sudo

CMD /usr/local/bin/run