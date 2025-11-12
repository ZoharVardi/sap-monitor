pipeline {
  agent any

  stages {
    stage('Pre-Deploy Health Check') {
      steps {
        script {
          // Call your FastAPI gate endpoint
          def resp = sh(
            script: 'curl -s http://host.docker.internal:8000/api/gate',
            returnStdout: true
          ).trim()

          echo "Gate response: ${resp}"

          //look for `"can_deploy":true`
          def canDeploy = resp.contains('"can_deploy":true')

          if (canDeploy) {
            echo " All systems healthy- ready to deploy."
            currentBuild.description = "Can deploy"
            currentBuild.result = "SUCCESS"
          } else {
            echo " Deployment gate closed- monitor failed."
            currentBuild.description = "Do NOT deploy"
            error("Pre-deploy check failed")
          }
        }
      }
    }
  }
}
