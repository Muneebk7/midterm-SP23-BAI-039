
// MIDTERM-SP23-BAI-039
// GitHub push -> retrain -> test -> Docker build -> deploy on EC2
// -> Docker Hub push -> email the person who pushed the changes.

pipeline {
    agent any

    triggers {
        GenericTrigger(
            genericVariables: [
                [key: 'PUSHER_EMAIL', value: '$.pusher.email'],
                [key: 'PUSHER_NAME', value: '$.pusher.name']
            ],
            causeString: 'GitHub push by $PUSHER_NAME',
            token: 'SP23-BAI-039-MIDTERM-WEBHOOK',
            printContributedVariables: true,
            printPostContent: false
        )
    }

    options {
        timestamps()
        disableConcurrentBuilds()
        timeout(time: 20, unit: 'MINUTES')
    }

    environment {
        STUDENT_ID = 'SP23-BAI-039'
        IMAGE = 'midterm-sp23-bai-039'
        CONTAINER = 'midterm-app'
        APP_PORT = '8000'
    }

    stages {

        stage('Fetch Latest Data') {
            steps {
                checkout scm

                script {
                    env.GIT_SHA = sh(
                        script: 'git rev-parse HEAD',
                        returnStdout: true
                    ).trim()

                    echo "Git commit: ${env.GIT_SHA}"
                    echo "GitHub pusher: ${env.PUSHER_NAME ?: 'Unknown'}"
                    echo "Pusher email: ${env.PUSHER_EMAIL ?: 'Not provided'}"
                }

                sh '''
                    echo "Checking dataset..."

                    CSV_FILE=$(find . -type f -name "*.csv" | head -n 1)

                    if [ -n "$CSV_FILE" ]; then
                        ROW_COUNT=$(($(wc -l < "$CSV_FILE") - 1))
                        echo "Dataset: $CSV_FILE"
                        echo "Dataset rows: $ROW_COUNT"
                    else
                        echo "No CSV dataset found."
                    fi
                '''
            }
        }

        stage('Train & Test') {
            steps {
                sh '''
                    echo "Building test image..."

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
                catchError(
                    buildResult: 'UNSTABLE',
                    stageResult: 'UNSTABLE'
                ) {
                    sh '''
                        set -a
                        . /etc/jenkins-dockerhub.env
                        set +a

                        echo "$DOCKERHUB_TOKEN" | docker login \
                            -u "$DOCKERHUB_USER" \
                            --password-stdin

                        docker tag \
                            $IMAGE:$BUILD_NUMBER \
                            $DOCKERHUB_USER/$IMAGE:$BUILD_NUMBER

                        docker tag \
                            $IMAGE:latest \
                            $DOCKERHUB_USER/$IMAGE:latest

                        docker push \
                            $DOCKERHUB_USER/$IMAGE:$BUILD_NUMBER

                        docker push \
                            $DOCKERHUB_USER/$IMAGE:latest

                        docker logout
                    '''
                }
            }
        }
    }

    post {
        always {
            script {
                // Only the GitHub pusher receives the email.
                // No commit-author, owner, or instructor fallback.

                def mailTo = (env.PUSHER_EMAIL ?: '').trim()
                def pusherName = (env.PUSHER_NAME ?: 'Unknown').trim()

                if (mailTo && mailTo.contains('@')) {

                    def status = currentBuild.currentResult ?: 'UNKNOWN'

                    echo "GitHub pusher: ${pusherName}"
                    echo "Sending notification only to: ${mailTo}"

                    def metrics = fileExists('metrics_live.json') ?
                        readFile('metrics_live.json') :
                        'n/a (deployment did not complete)'

                    writeFile(
                        file: 'mail_body.txt',
                        text: """Student Reg No : ${env.STUDENT_ID}
Job            : ${env.JOB_NAME} #${env.BUILD_NUMBER}
Result         : ${status}
Git commit     : ${env.GIT_SHA ?: 'n/a'}
Pushed by      : ${pusherName}
Pusher email   : ${mailTo}
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

                } else {
                    echo 'GitHub did not provide a valid pusher email.'
                    echo 'Skipping email notification. No fallback recipients will be used.'
                }
            }
        }
    }
}
