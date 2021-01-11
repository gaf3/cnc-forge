pipeline {
    agent any

    stages {
        stage('build api') {
            steps {
                dir('api') {
                    sh 'make build'
                }
            }
        }
        stage('test api') {
            steps {
                dir('api') {
                    sh 'make test'
                }
            }
        }
        stage('lint api') {
            steps {
                dir('api') {
                    sh 'make lint'
                }
            }
        }
        stage('build daemon') {
            steps {
                dir('daemon') {
                    sh 'make build'
                }
            }
        }
        stage('test daemon') {
            steps {
                dir('daemon') {
                    sh 'make test'
                }
            }
        }
        stage('lint daemon') {
            steps {
                dir('daemon') {
                    sh 'make lint'
                }
            }
        }
        stage('build gui') {
            steps {
                dir('gui') {
                    sh 'make build'
                }
            }
        }
        stage('push api') {
            when {
                branch 'master'
            }
            steps {
                dir('api') {
                    sh 'make push'
                }
            }
        }
        stage('push daemon') {
            when {
                branch 'master'
            }
            steps {
                dir('daemon') {
                    sh 'make push'
                }
            }
        }
        stage('push gui') {
            when {
                branch 'master'
            }
            steps {
                dir('gui') {
                    sh 'make push'
                }
            }
        }
    }
}
