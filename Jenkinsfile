
pipeline {
    agent any

    triggers {
        pollSCM('H/2 * * * *')
    }

    options {
        timestamps()
        disableConcurrentBuilds()
        timeout(time: 30, unit: 'MINUTES')
    }

    environment {
        AWS_REGION = 'ap-south-2'
        ECR_REPOSITORY = 'aa-ecs-jenkins-app'
        ECS_CLUSTER = 'aa-jenkins-cluster'
        ECS_SERVICE = 'aa-jenkins-service'
        TASK_FAMILY = 'aa-jenkins-task'
        CONTAINER_NAME = 'aa-jenkins-container'
        ALB_URL = 'http://aa-jenkins-alb-2046605292.ap-south-2.elb.amazonaws.com/'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                sh 'git status --short'
            }
        }

        stage('Test') {
            steps {
                sh '''
                    set -eu
                    python3 -m py_compile app.py
                    grep -q "def health" app.py
                    grep -q "IMAGE_PLACEHOLDER" task-definition.json
                    echo "Basic application and task definition checks passed"
                '''
            }
        }

        stage('Build Docker Image') {
            steps {
                script {
                    env.IMAGE_TAG =
                        "${env.BUILD_NUMBER}-${env.GIT_COMMIT.substring(0, 7)}"
                }

                sh '''
                    set -eu
                    docker build \
                      -t "${ECR_REPOSITORY}:${IMAGE_TAG}" .
                    docker image inspect \
                      "${ECR_REPOSITORY}:${IMAGE_TAG}" >/dev/null
                '''
            }
        }

        stage('Push Image to ECR') {
            steps {
                sh '''
                    set -eu

                    AWS_ACCOUNT_ID=$(aws sts get-caller-identity \
                      --query Account --output text)

                    REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
                    IMAGE_URI="${REGISTRY}/${ECR_REPOSITORY}:${IMAGE_TAG}"

                    aws ecr get-login-password \
                      --region "${AWS_REGION}" \
                      | docker login \
                          --username AWS \
                          --password-stdin "${REGISTRY}"

                    docker tag "${ECR_REPOSITORY}:${IMAGE_TAG}" "${IMAGE_URI}"
                    docker push "${IMAGE_URI}"

                    echo "${IMAGE_URI}" > deployed-image.txt
                '''
            }
        }

        stage('Deploy to ECS') {
            steps {
                sh '''
                    set -eu

                    IMAGE_URI=$(cat deployed-image.txt)

                    sed "s|IMAGE_PLACEHOLDER|${IMAGE_URI}|g" \
                      task-definition.json > rendered-task-definition.json

                    REVISION=$(aws ecs register-task-definition \
                      --cli-input-json file://rendered-task-definition.json \
                      --region "${AWS_REGION}" \
                      --query 'taskDefinition.revision' \
                      --output text)

                    echo "Registered task definition revision: ${REVISION}"

                    aws ecs update-service \
                      --cluster "${ECS_CLUSTER}" \
                      --service "${ECS_SERVICE}" \
                      --task-definition "${TASK_FAMILY}:${REVISION}" \
                      --region "${AWS_REGION}" \
                      --output json

                    aws ecs wait services-stable \
                      --cluster "${ECS_CLUSTER}" \
                      --services "${ECS_SERVICE}" \
                      --region "${AWS_REGION}"
                '''
            }
        }

        stage('Verify Deployment') {
            steps {
                sh '''
                    set -eu

                    echo "Checking application health..."

                    for attempt in $(seq 1 12); do
                      if curl --fail --silent --show-error \
                        --max-time 10 "${ALB_URL}/health"; then
                        echo ""
                        echo "Deployment verification successful"
                        exit 0
                      fi

                      echo "Health check attempt ${attempt}/12 failed; retrying..."
                      sleep 10
                    done

                    echo "Application health verification failed"
                    exit 1
                '''
            }
        }
    }

    post {
        success {
            echo 'SUCCESS: Image pushed and ECS deployment verified.'
        }

        failure {
            echo 'FAILED: Check the failed stage and its console output.'
        }

        always {
            archiveArtifacts artifacts: 'deployed-image.txt',
                             allowEmptyArchive: true
        }
    }
}
