// MIDTERM-SP23-BAI-039
// GitHub push -> retrain -> test -> Docker build -> deploy on EC2
// -> Docker Hub push -> email the person who committed (+ instructor when needed).

pipeline {
    agent any

    // GitHub push webhook -> http://<ec2>:8080/github-webhook/
    triggers { githubPush() }

    options {
        timestamps()
        disableConcurrentBuilds()
        timeout(time: 20, unit: 'MINUTES')
        // Checkout happens inside the first stage, so if it fails the post{} block
        // still has a workspace + env vars and can send the failure e-mail.
        skipDefaultCheckout(true)
    }

    environment {
        STUDENT_ID = 'SP23-BAI-039'
        IMAGE      = 'midterm-sp23-bai-039'
        CONTAINER  = 'midterm-app'
        APP_PORT   = '8000'
    }

    stages {

        stage('Fetch Latest Data') {
            steps {
                script {
                    // Retry the checkout; wipe the workspace between attempts in case it is in a bad state.
                    retry(3) {
                        try {
                            checkout scm
                        } catch (err) {
                            echo "Checkout failed (${err}); cleaning workspace before retry"
                            deleteDir()
                            sleep 5
                            throw err
                        }
                    }

                    env.GIT_SHA      = sh(script: 'git rev-parse HEAD',        returnStdout: true).trim()
                    env.COMMIT_EMAIL = sh(script: 'git log -1 --format=%ae',   returnStdout: true).trim()
                    env.COMMIT_NAME  = sh(script: 'git log -1 --format=%an',   returnStdout: true).trim()

                    echo "Git commit: ${env.GIT_SHA}"
                    echo "Committed by: ${env.COMMIT_NAME} <${env.COMMIT_EMAIL}>"
                }

                sh '''
                    echo "Checking dataset..."
                    if [ -f dataset/train.csv ]; then
                        echo "Dataset rows: $(($(wc -l < dataset/train.csv) - 1))"
                    else
                        echo "dataset/train.csv not found."
                    fi
                '''
            }
        }

        stage('Train & Test') {
            steps {
                sh '''
                    echo "Building test image (runs train.py + pytest)..."
                    docker build \
                        --target test \
                        --build-arg GIT_COMMIT=$GIT_SHA \
                        -t $IMAGE:test .
                '''
            }
        }

        stage('Build Docker Image') {
            steps {
                sh '''
                    echo "Building runtime image..."
                    docker build \
                        --target runtime \
                        --build-arg GIT_COMMIT=$GIT_SHA \
                        -t $IMAGE:$BUILD_NUMBER \
                        -t $IMAGE:latest .
                '''
            }
        }

        stage('Deploy to EC2') {
            steps {
                sh '''
                    rm -f metrics_live.json

                    echo "Removing previous container..."
                    docker rm -f $CONTAINER || true

                    echo "Starting new container..."
                    docker run -d \
                        --name $CONTAINER \
                        --restart unless-stopped \
                        -p $APP_PORT:$APP_PORT \
                        $IMAGE:$BUILD_NUMBER

                    echo "Waiting for application to become available..."
                    for i in $(seq 1 30); do
                        if curl --fail --silent \
                            http://localhost:$APP_PORT/metrics \
                            -o metrics_live.json; then
                            echo "Application is running."
                            break
                        fi
                        echo "Waiting for application... ($i/30)"
                        sleep 2
                    done

                    if [ ! -s metrics_live.json ]; then
                        echo "Application deployment or metrics check failed."
                        docker logs $CONTAINER || true
                        exit 1
                    fi

                    echo "Live metrics:"
                    cat metrics_live.json

                    echo "Verifying deployed commit..."
                    grep -q "$GIT_SHA" metrics_live.json || {
                        echo "Deployed commit does not match expected commit."
                        exit 1
                    }

                    echo "Keeping only the latest 3 numbered images..."
                    docker images "$IMAGE" \
                        --format '{{.Tag}}' \
                        | grep -E '^[0-9]+$' \
                        | sort -rn \
                        | tail -n +4 \
                        | while read tag; do
                            docker rmi "$IMAGE:$tag" || true
                          done
                '''
            }
        }

        stage('Push to Docker Hub') {
            steps {
                // After the deploy, so a Docker Hub problem can never block the redeploy.
                catchError(buildResult: 'UNSTABLE', stageResult: 'UNSTABLE') {
                    sh '''
                        set -a
                        . /etc/jenkins-dockerhub.env
                        set +a

                        echo "$DOCKERHUB_TOKEN" | docker login \
                            -u "$DOCKERHUB_USER" \
                            --password-stdin

                        docker tag $IMAGE:$BUILD_NUMBER $DOCKERHUB_USER/$IMAGE:$BUILD_NUMBER
                        docker tag $IMAGE:latest        $DOCKERHUB_USER/$IMAGE:latest

                        docker push $DOCKERHUB_USER/$IMAGE:$BUILD_NUMBER
                        docker push $DOCKERHUB_USER/$IMAGE:latest

                        docker logout
                    '''
                }
            }
        }
    }

    post {
        always {
            script {
                // Recipients:
                //  * the person who made the commit (if their address is usable)
                //  * PLUS the instructor whenever the commit is not the owner's (e.g. the autograder),
                //    or when no usable committer address is available - so the graded mail is never lost.
                //  * if the owner's own commit has no usable address, fall back to the owner.
                // Literals are used on purpose: this block must work even if the build failed very early.
                def instructor = 'qasimalik@gmail.com'
                def owner      = 'kmoneeb499@gmail.com'

                def ce = (env.COMMIT_EMAIL ?: '').trim().toLowerCase()
                def cn = (env.COMMIT_NAME ?: '').trim()
                def deliverable = ce.contains('@') && !ce.endsWith('noreply.github.com')
                def isOwner = (ce == owner) || (cn == 'Muneebk7') || (cn == 'Muneeb Khan') || ce.contains('+muneebk7@')

                def recipients = []
                if (deliverable) { recipients.add(ce) }
                if (!isOwner && !recipients.contains(instructor)) { recipients.add(instructor) }
                if (recipients.isEmpty()) { recipients.add(owner) }
                def mailTo = recipients.join(',')

                def status = currentBuild.currentResult ?: 'UNKNOWN'
                echo "Committer: ${cn ?: 'unknown'} <${ce ?: 'unknown'}>  -> mailing: ${mailTo}"

                def metrics = fileExists('metrics_live.json') ?
                    readFile('metrics_live.json') :
                    'n/a (deployment did not complete)'

                writeFile(
                    file: 'mail_body.txt',
                    text: """Student Reg No : ${env.STUDENT_ID}
Job            : ${env.JOB_NAME} #${env.BUILD_NUMBER}
Result         : ${status}
Git commit     : ${env.GIT_SHA ?: 'n/a'}
Committed by   : ${cn ?: 'n/a'} <${ce ?: 'n/a'}>
Build URL      : ${env.BUILD_URL}
Metrics URL    : http://13.48.137.248:${env.APP_PORT}/metrics

Live /metrics:
${metrics}
"""
                )

                try {
                    withEnv([
                        "MAIL_TO=${mailTo}",
                        "MAIL_SUBJECT=[${env.STUDENT_ID}] MIDTERM build #${env.BUILD_NUMBER} - ${status}",
                        'MAIL_BODY_FILE=mail_body.txt'
                    ]) {
                        sh '''
                            set -a
                            . /etc/jenkins-smtp.env
                            set +a

                            python3 scripts/send_email.py
                        '''
                    }
                } catch (err) {
                    echo "Email notification failed: ${err}"
                    currentBuild.result = 'UNSTABLE'
                }
            }
        }
    }
}
