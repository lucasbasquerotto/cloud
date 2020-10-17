FROM lucasbasquerotto/ansible:0.0.2

COPY container/run.sh /usr/local/bin/run
COPY container/ansible /usr/main/ansible
COPY tasks /usr/main/ansible/external-tasks

CMD /usr/local/bin/run