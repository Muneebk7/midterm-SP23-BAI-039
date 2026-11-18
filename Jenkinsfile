// MIDTERM-SP23-BAI-039 : GitHub push -> retrain -> test -> Docker build -> deploy on EC2 -> email
pipeline {
    agent any

    triggers { githubPush() }

    options {
        timestamps()
        disableConcurrentBuilds()
        timeout(time: 20, unit: 'MINUTES')
    }

    environment {
        STUDENT_ID = 'SP23-BAI-039'
        IMAGE      = 'midterm-sp23-bai-039'
        CONTAINER  = 'midterm-app'
        APP_PORT   = '8000'
        MAIL_TO    = 'qasimalik@gmail.com'
        MAIL_CC    = 'kmoneeb499@gmail.com'
    }

    stages {
        stage('Fetch latest data') {
            steps {
                checkout scm
                script {
                    env.GIT_SHA = sh(returnStdout: true, script: 'git rev-parse HEAD').trim()
                }
                sh '''
                    git log -1 --pretty="Commit: %h %an - %s"
                    echo "dataset/train.csv rows (incl. header): $(wc -l < dataset/train.csv)"
                '''
            }
        }

        stage('Train & Test') {
            steps {
                // The Dockerfile `test` target runs train.py and then pytest.
                sh '''
                    docker build --target test \
                        --build-arg GIT_COMMIT=$GIT_SHA -t $IMAGE:test .
                '''
            }
        }

        stage('Build image') {
            steps {
                sh '''
                    docker build --target runtime \
                        --build-arg GIT_COMMIT=$GIT_SHA \
                        -t $IMAGE:$BUILD_NUMBER -t $IMAGE:latest .
                '''
            }
        }

        stage('Deploy to EC2') {
            steps {
                sh '''
                    docker rm -f $CONTAINER 2>/dev/null || true
                    docker run -d --name $CONTAINER --restart unless-stopped \
                        -p $APP_PORT:8000 $IMAGE:$BUILD_NUMBER

                    for i in $(seq 1 30); do
                        if curl -fsS http://localhost:$APP_PORT/metrics > metrics_live.json; then break; fi
                        sleep 2
                    done
                    echo "Live /metrics:"; cat metrics_live.json; echo
                    grep -q "$GIT_SHA" metrics_live.json   # deployed model must come from this commit

                    # keep only the 3 most recent numbered images
                    docker images $IMAGE --format "{{.Tag}}" | grep -E "^[0-9]+$" | sort -rn | tail -n +4 \
                        | xargs -r -I{} docker rmi $IMAGE:{} || true
                '''
            }
        }
    }

    post {
        always {
            script {
                def status = currentBuild.currentResult
                def metrics = fileExists('metrics_live.json') ? readFile('metrics_live.json') : 'n/a (deploy did not complete)'
                writeFile file: 'mail_body.txt', text: """Student Reg No : ${env.STUDENT_ID}
Job            : ${env.JOB_NAME}  #${env.BUILD_NUMBER}
Result         : ${status}
Git commit     : ${env.GIT_SHA ?: 'n/a'}
Build URL      : ${env.BUILD_URL}
Metrics URL    : http://13.48.137.248:${env.APP_PORT}/metrics

Live /metrics:
${metrics}
"""
                try {
                    // Gmail login lives on the EC2 host in /etc/jenkins-smtp.env (root:jenkins, mode 640), never in git.
                    withEnv(["MAIL_SUBJECT=[${env.STUDENT_ID}] MIDTERM build #${env.BUILD_NUMBER} - ${status}",
                             'MAIL_BODY_FILE=mail_body.txt']) {
                        sh 'set -a; . /etc/jenkins-smtp.env; set +a; python3 scripts/send_email.py'
                    }
                } catch (err) {
                    echo "Email failed: ${err}"
                    currentBuild.result = 'UNSTABLE'
                }
            }
        }
    }
}
