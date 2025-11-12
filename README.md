🧠 SAP Monitoring Control Panel (FastAPI + Prometheus + Grafana + Jenkins)

This project monitors multiple SAP API endpoints and exposes health metrics to Prometheus.
It provides a deployment gate API (/api/gate) used by Jenkins pipelines to determine whether deployment is allowed, based on the live health status of monitored SAP services.

The repository also includes a Java example app (simple-java-maven-app/) with its own Jenkinsfile for demonstration purposes.


🚀 Features

✅ Live health checks of SAP APIs

📈 Prometheus metrics (/metrics) for uptime and latency

🔐 Deployment gate API (/api/gate) for Jenkins automation

🧩 Grafana dashboard embedded in FastAPI web UI

🐳 Dockerized services (FastAPI, Prometheus, Grafana)

⚙️ Background thread for continuous health checks



🧱 Two Jenkins pipelines:

Jenkinsfile → pipeline for SAP Monitor

simple-java-maven-app/Jenkinsfile → Example Java Main CI/CD







⚙️ Installation (Local)

1️⃣ Clone the repository

git clone https://github.com/zoharvardi/sap-monitor.git
cd sap-monitor


2️⃣ Install dependencies

pip install -r requirements.txt


3️⃣ Run the app

uvicorn monitor_app:monitor_app --reload --port 8000

🔗 API Endpoints

Endpoint	Method	Type	Description
/	GET	HTML	Dashboard with Grafana and gate status
/metrics	GET	Prometheus text	For Prometheus scraping
/api/gate	GET	JSON	Returns {"can_deploy": true/false} for Jenkins


📊 Prometheus Metrics

Metric	            Type	            Description
endpoint_up{url}	Gauge	1 if endpoint returns 2xx, else 0
endpoint_latency_seconds{url}	Summary	Latency for each SAP endpoint
monitor_can_deploy	Gauge	1 if all endpoints OK, else 0

🧠 Deployment Gate Logic

A background thread runs continuously and:

Checks all URLs in SAP_URLS every 20 seconds

Records uptime and latency metrics

Sets monitor_can_deploy = 1 only if all endpoints are healthy

Example:

{"can_deploy": true}

Used by Jenkins to automatically stop deployment if any endpoint fails.



🧱 Docker Setup

Build and run locally:
docker build -t zoharvardi/sap-monitor:latest .
docker run -d -p 8000:8000 zoharvardi/sap-monitor:latest

Run Prometheus & Grafana:
docker run -d -p 9090:9090 prom/prometheus
docker run -d -p 3000:3000 grafana/grafana


🧩 Jenkins Integration

The project includes two connected Jenkins pipelines that demonstrate a realistic CI/CD workflow:

Pre-Deploy Pipeline – Checks the FastAPI monitoring service (/api/gate) to ensure all SAP endpoints are healthy.
If any are failing, this job marks the build as failed and blocks further deployment.

Deploy Pipeline – Automatically triggered whenever new code is pushed to the repository.
It first calls the Pre-Deploy job to confirm the system is healthy, and only then proceeds with the full build-test-deploy sequence for the demo Java app (simple-java-maven-app).

Together, they simulate a production-grade setup where deployments are gated by live system health, integrating the SAP Monitor, Prometheus metrics, and Jenkins automation into a continuous deployment workflow. 



📈 Grafana Setup

Run Grafana:

docker run -d -p 3000:3000 grafana/grafana


Add Prometheus data source:

URL: http://host.docker.internal:9090

Import a dashboard or use the built-in iframe:

<iframe src="http://localhost:3000/d/your_dashboard_id?orgId=1&refresh=30s"
        width="100%" height="400" frameborder="0"></iframe>




🧠 Tech Stack

Component	      
FastAPI	REST API and monitoring dashboard
Prometheus Client	
Grafana	Visualization layer
Docker	Containerization
Jenkins	CI/CD pipelines (Python + Java examples)
Maven	Java build automation (sample app)




