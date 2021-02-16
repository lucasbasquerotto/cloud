FROM lucasbasquerotto/ansible:1.0.0

RUN apt-get update \
 && apt-get install -y --no-install-recommends git \
 && rm -rf /var/lib/apt/lists/*

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

# RUN yes | pip install docker-py 'dopy>=0.3.5,<=0.3.5' \
#  && yes | pip3 install boto boto3 botocore

CMD /usr/local/bin/run