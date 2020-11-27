FROM lucasbasquerotto/ansible:0.0.2

RUN pip3 install pyyaml

COPY container/run.sh /usr/local/bin/run
COPY container/ansible /usr/main/ansible
COPY tasks/util /usr/main/ansible/tasks/util

RUN echo 'exec "${@}"' > /usr/local/bin/sudo \
 && chmod +x /usr/local/bin/sudo

CMD /usr/local/bin/run