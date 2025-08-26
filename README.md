### KUBERNETES OBJECTS I HAVE USED
-   ***Namespace***
-   ***ConfigMap***
-   ***Secrets***
-   ***HorizontalPodAutoscaler***
-   ***ResourceQuota (Namespace level resource management)*** 
-   ***LimitRange (Container level resource management)***
-   ***Service***
-   ***Job***
-   ***Deployment***
-   ***StatefulSet***

### NAMES OF KUBERNETES OBJECTS
-   ##### KUBERNETES
        -   Namespaces: xray-api
        -   ResourceQuota: python-api-rq
        -   LimitRange: python-api-lr
        -   HorizontalPodAutoscaler(Inner API): python-api-hpa 
        -   HorizontalPodAutoscaler(Outer API): python-api-mng-hpa 
-   ##### DATABASE
        -   ConfigMap: db-config
        -   Secrets: db-secrets
        -   Service: db-svc
        -   Service-Headless: db-svc-hl
        -   StatefulSet: postgres
        -   Job ConfigMap: db-init-sql
        -   Job: db-init
-   ##### INNER API(Model API)
        -   NetworkPolicy: allow-only-flask
        -   Service: python-svc
        -   Deployment: python-api
-   ##### OUTER API(Gateway API)
        -   Service: python-svc-mng
        -   Deployment: python-api-mng

### COMPONENTS OF APPLICATION
    -   PostgreSQL
    -   Inner/Model API with Flask(Python)
    -   Outer/Gateway API with Flask(Python)

### THE ADDONS I HAVE USED IN KUBERNETES
    -   metrics-server -> for HPA
    -   ingress -> for HTTP access
    -   cilium -> for NetworkPolicy enforcement

### WHAT DID I DO(Kubernetes)
-   **Created a namespace**
    -   I created a namespace for workload isolation.
-   **Applied HorizontalPodAutoscaler**
    -   I applied HPA to both the inner and outer/gateway services. I defined minimum and maximum replica counts and set CPU utilization targets.

### WHAT DID I DO(Database)
-   **Database with StatefulSet**
    -   I have used a StatefulSet because a database needs a permanent volume for storing data.
-  **Database Configs with ConfigMap**
    -   I have stored non-sensitive data such as the database host and database name here.
-   **Database Sensitive Data with Secret**
    -   I have stored sensitive data such as the database user and password here.
-   **Database Service**
    -   This service exposes the database on a specific port with type ClusterIP (accessible only inside the cluster).
-   **Database Service(Headless)**
    -   This service provides DNS records for each database Pod and ensures correct routing between them.
-   **Database Init Job**
    -   Used for running initialization SQL scripts (such as creating schemas or tables) when the database starts.

### WHAT DID I DO(Model API)
-   **API Service**
    -   This service exposes the Model API on a specific port with type ClusterIP (works only inside the cluster). Pods are accessible through this service.
-   **API Deployment**
    -   This deployment mounts the ConfigMap and Secret for database access and ensures the correct workflow of the application.

### WHAT DID I DO(Outer API/Gateway API)
-   **API Config**
    -   This ConfigMap defines the base URL of the Model API for accessing it through the service.
-   **API Service**
    -   This service exposes the Gateway API with type NodePort (accessible from outside the cluster) using HTTP, and binds the external node port as 30080.
-   **API Deployment**
    -   This deployment uses the ConfigMap and Secret of the Gateway API, and defines resource requests and limits for handling incoming requests.

### WHAT DID I DO(Network)
-   **Gateway/Outer Service to Model Service**
    -   I have defined a "NetworkPolicy" for the Model API. This policy ensures that only the Gateway/Outer service can access the Model API.

### WHAT I AM WORKIN' ON?
-   I am currently working on kubernetes security configuration. 
    Things i am going to work about:
    -   Kyverno (STATUS: Not Started)
    -   RBAC (STATUS: Not Started)
    -   Ingress Configuration (STATUS: Not Started)
    -   Kubernetes Security Standards (STATUS: In Progress)