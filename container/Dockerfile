FROM lucasbasquerotto/ansible:0.0.2

COPY container/run.sh /usr/local/bin/run
COPY container/ansible /usr/main/ansible
COPY tasks /usr/main/ansible/external-tasks

RUN echo 'exec "${@}"' > /usr/local/bin/sudo \
 && chmod +x /usr/local/bin/sudo

CMD /usr/local/bin/run