## DESCRIPTION
### KUBERNETES OBJECTS WHICH IS USED
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
-   ***ServiceAccount***
-   ***PodDisruptionBudget***
-   ***RBAC***

### COMPONENTS OF APPLICATION
    -   PostgreSQL
    -   Image Classification API with "Flask"

## ABOUT SYSTEM
### NAMES OF KUBERNETES OBJECTS
-   ##### KUBERNETES CORE
        -   Namespaces: xray-api
        -   ResourceQuota: python-api-rq
        -   LimitRange: python-api-lr
-   ##### DATABASE
        -   ConfigMap: db-config
        -   Secrets: db-secrets
        -   Service: postgres-hl
        -   StatefulSet: postgres
        -   Job ConfigMap: db-init-sql
        -   Job: db-init
-   ##### API
        -   Service: python-api-svc
        -   ServiceAccount: python-api-sa
        -   Deployment: python-api
        -   HorizontalPodAutoscaler: python-api-hpa 
        -   PodDisruptionBudget: python-api-pdb
-   ##### NETWORK
        -   NetworkPolicy: default-deny-all
        -   NetworkPolicy: allow-dns
        -   NetworkPolicy: allow-api-public-ingress
        -   NetworkPolicy: allow-api-egress-to-db
        -   NetworkPolicy: allow-db-ingress
        -   NetworkPolicy: allow-dbinit-egress-to-db
-   ##### CLUSTER POLICY ENFORCEMENT WITH **KYVERNO**
        -   ClusterPolicy: enforce-pod-security-restricted
            -   require-seccomp
            -   require-container-security
        -   ClusterPolicy: require-apparmor
            -   apparmor-runtime-default
        -   ClusterPolicy: sa-automount-disabled
            -   pod-sa-automount
        -   ClusterPolicy: disallow-latest-tag
            -   no-latest
        -   ClusterPolicy: require-resources-and-probes
            -   resource-limits
            -   health-probes

### THE USED ADDONS IN KUBERNETES
    -   metrics-server -> for HPA
    -   ingress -> for HTTP access
    -   cilium -> for NetworkPolicy enforcement

## SECURITY
### POD SECURITY STANDARDS
-   #### Namespace Level
    -   Containers are working as "non-root" user.
    -   No "privileged" containers. 
    -   "HostPath" volumes must be forbidden. 
    -   "AppArmor" must be applied. -> Kuburnetes "default"
    -   "Seccomp" profile must not be set to uncofined (***Kubernetes applies auto***)

### MANIFESTS OF KUBERNETES (in "core" folder)
-   **Created a namespace**
    -   A namespace is created for workload isolation.
-   **Determined resource quota and limit range**
    -   Limit ranges are defined for each container, and resource quotas are specified for the system.

### MANIFESTS OF DATABASE (in "database" folder)
-  **Database Configs**
    -   Non-sensitive data such as database host and database name are stored here.
-   **Database Sensitive Data**
    -   Sensitive data such as database user and password are stored here.
-   **Database StatefulSet**
    -   A StatefulSet is used because the database requires a persistent volume for storing data.
-   **Database Headless Service**
    -   Provides DNS records for each database Pod and ensures correct routing between them.
-   **Database Init Job**
    -   Runs initialization SQL scripts (e.g., creating schemas or tables) when the database starts.

### MANIFESTS OF API (in "api" folder)
-   **API Service**
    -   Exposes the model API on a specific port using ClusterIP (accessible only inside the cluster). API Pods are reachable through this service.
-   **API Deployment**
    -   Mounts the ConfigMap and Secret for database access and ensures the application workflow runs correctly.

### MANIFESTS OF NETWORK (in "network" folder)
-   **Default Deny All Network Policy**
    -   All traffic is denied by default.
-   **Allow DNS Network Policy**
    -   Allows DNS resolution.
-   **Allow Requests to API Endpoint Network Policy**
    -   Allows inbound traffic to the API endpoint.
-   **Allow Requests to Postgres from API Network Policy**
    -   Allows the API to connect to Postgres for saving data.
-   **Allow Requests to API and Database Init Job from Postgres Network Policy**
    -   Allows communication between Postgres, the API, and the DB Init Job.
-   **Allow Requests to Postgres from DB Init Job Network Policy**
    -   Allows the DB Init Job to connect to Postgres for creating the database and initializing tables.

### MANIFESTS OF CLUSTER with ***Kyverno*** (in "cluster" folder)
-   **Pod Restriction Cluster Policy**
    -   All Pods must use seccompProfile. Each container must run as non-root, use readOnlyRootFilesystem, have privilege escalation disabled, and drop all Linux capabilities.
-   **Pod AppArmor Cluster Policy**
    -   Each Pod must have AppArmor enabled.
-   **Pod Service Account AutoMount Cluster Policy**
    -   Pods must not automatically mount ServiceAccount tokens unless explicitly required.
-   **Image Will Not Work If It Has Latest Tag Cluster Policy**
    -   Images using the latest tag are disallowed to prevent non-deterministic deployments.
-   **Pod Requires Resources and Probes Cluster Policy**
    -   Each container must specify CPU/Memory requests & limits, and must include both a ReadinessProbe and LivenessProbe.

## INSTALL & RUN
-   **1 - Run "install.sh"**
-   **2 - Run "start.sh"**
-   **(Optional) - Run "database.sh" if you want to access into database shell.**