# Jenkins com Python (para os testes) e os plugins de Pipeline ja instalados
FROM jenkins/jenkins:lts-jdk17
USER root
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-venv && \
    rm -rf /var/lib/apt/lists/* && \
    git config --system --add safe.directory '*' && \
    mkdir -p /publicacao && chown jenkins:jenkins /publicacao
USER jenkins
ENV JAVA_OPTS="-Djenkins.install.runSetupWizard=false -Dhudson.plugins.git.GitSCM.ALLOW_LOCAL_CHECKOUT=true"
RUN jenkins-plugin-cli --plugins workflow-aggregator git pipeline-stage-view
COPY --chown=jenkins:jenkins admin.groovy /usr/share/jenkins/ref/init.groovy.d/admin.groovy
