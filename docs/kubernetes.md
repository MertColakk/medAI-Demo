# OTHER PAGES (Click for navigate)
* [Main Page](../README.md)
*[Security](./security.md)
* [Code Overviews](./code.md)

# CONTENTS
* [About Kubernetes](#about-kubernetes)
* [Operators](#operators)
* [Kubernetes Manifests Descriptions](#kubernetes-manifest-descriptions)

## ABOUT KUBERNETES
### KUBERNETES OBJECTS WHICH ARE USED
-   Namespace
-   ConfigMap
-   Secrets
-   HorizontalPodAutoscaler
-   ResourceQuota 
-   NetworkPolicy
-   ValidatingAdmissionPolicy
-   LimitRange 
-   Service
-   ServiceAccount
-   Deployment
-   StatefulSet
-   ServiceAccount
-   PodDisruptionBudget
-   ClusterRoleBinding
-   ClusterRole
-   CustomResourceDefinition

### NAMES OF KUBERNETES OBJECTS
-   ##### KUBERNETES CORE
        -   Namespaces: xray-api
        -   ResourceQuota: python-api-rq
        -   LimitRange: python-api-lr
-   ##### DATABASE (**__PostgreSQL__**)
        -   ConfigMap: db-config
        -   Secrets: db-secrets
        -   Service: postgres-hl
        -   StatefulSet: postgres
-   ##### API OPERATOR (**__Kopf__**)
        -   CustomResourceDefinition: XrayApp
        -   ServiceAccount: xray-operator
        -   Role: xray-operator-role
        -   RoleBinding: xray-operator-rb
        -   Deployment: xray-operator
        -   PolicyException: allow-no-apparmor-in-xray
    -   ###### API (**__Python__**)
            -   Service: python-api-svc
            -   ServiceAccount: python-api-sa
            -   Deployment: python-api
            -   HorizontalPodAutoscaler: python-api-hpa 
            -   PodDisruptionBudget: python-api-pdb
-   ##### NETWORK (**__Kyverno__**)
        -   NetworkPolicy: default-deny-all
        -   NetworkPolicy: allow-dns
        -   NetworkPolicy: allow-api-public-ingress
        -   NetworkPolicy: allow-api-egress-to-db
        -   NetworkPolicy: allow-db-ingress
        -   NetworkPolicy: allow-dbinit-egress-to-db

### THE USED ADDONS IN KUBERNETES
    -   metrics-server -> for HPA
    -   ingress -> for HTTP access
    -   cilium -> for NetworkPolicy enforcement

## OPERATORS
    -   PostgreSQL Operator
    -   Image Classification API Operator

## KUBERNETES MANIFESTS DESCRIPTIONS
### MANIFESTS OF CORE 
-   **Created a namespace**
    -   A namespace is created for workload isolation.
-   **Determined resource quota and limit range (in "k8s/00-core.yaml" file)** 
    -   Limit ranges are defined for each container, and resource quotas are specified for the system.

### MANIFESTS OF DATABASE (in "k8s/03-db.yaml" file)
-  **Database Configs**
    -   Non-sensitive data such as database host and database name are stored here.
-   **Database Sensitive Data**
    -   Sensitive data such as database user and password are stored here.
-   **Database StatefulSet**
    -   A StatefulSet is used because the database requires a persistent volume for storing data.
-   **Database Headless Service**
    -   Provides DNS records for each database Pod and ensures correct routing between them.

### MANIFESTS OF OPERATOR (in "k8s/05-operator.yaml" folder)
-   **Operator CRD (in "k8s/04-operator-crd.yaml" folder)**
    -   Defines a Custom Resource that extends the Kubernetes API with new object types managed by the operator.
-   **Operator Service Account**
    -   Provides an identity for the operator pods to interact with the Kubernetes API.
-   **Operator Role**
    -   Defines the permissions (rules) the operator needs to manage resources.
-   **Operator RoleBinding**
    -   Binds the Service Account to the Role, granting the operator the required permissions.
-   **Operator Deployment**
    -   Runs the operator as a Deployment inside the cluster, ensuring it is available and can reconcile custom resources.

    #### MANIFESTS OF API (in "app/op/operator/main.py")
    -   **API Service Account**
        -   Provides an identity for the API pods to securely interact with Kubernetes resources (if needed).
    -   **API Service**
        -   Exposes the API application on a specific port. Typically uses ClusterIP for internal access, or NodePort/LoadBalancer if external access is required.
    -   **API Deployment**
        -   Defines how the API application pods are created, managed, and updated (including mounting ConfigMaps and Secrets for configuration and database access).
    -   **API HPA**
        -   Automatically scales the number of API pods based on CPU/memory usage or custom metrics.
    -   **API PDB**
        -   Ensures a minimum number of API pods remain available during voluntary disruptions.

### MANIFESTS OF NETWORK (in "k8s/03-network.yaml" file)
-   **Default Deny All Network Policy**
    -   Denies all ingress and egress traffic by default for every Pod in the xray-api namespace. This ensures a “zero trust” baseline.
-   **Allow DNS Network Policy**
    -   Permits Pods in the xray-api namespace to send DNS queries (UDP/TCP on port 53) to CoreDNS Pods in the kube-system namespace.
-   **Allow Public Ingress to API (8081)**
    -   Allows external traffic from any source to reach Pods labeled app: xray-api on TCP port 8081. This exposes the API service.
-   **Allow API Egress to Database (5432)**
    -   Permits Pods labeled app: xray-api to connect outbound to Pods labeled app: postgres on TCP port 5432.
-   **Allow Database Ingress from API (5432)**
    -   Permits Pods labeled app: postgres to accept inbound connections only from Pods labeled app: xray-api on TCP port 5432.
-   **Allow Operator Ingress from API (8081)**
    -   Allows Pods labeled app: xray-operator to receive inbound traffic from Pods labeled app: xray-api on TCP port 8081.
-   **Allow Operator Egress to Kubernetes API Server (443)**
    -   Grants Pods labeled app: xray-operator permission to connect to the Kubernetes API server over TCP port 443.
    -   IP blocks for both the cluster service address (10.96.0.1/32) and Minikube host address (192.168.49.2/32) are included.
-   **Kyverno Default Deny**
    -   Applies a default-deny rule for all Pods in the kyverno namespace, blocking all ingress and egress unless explicitly allowed.
-   **Kyverno Allow DNS**
    -   Permits Pods in the kyverno namespace to resolve DNS by connecting to CoreDNS in kube-system on port 53 (UDP/TCP).
-   **Kyverno Allow API Server**
    -   Allows Pods in the kyverno namespace to egress to the Kubernetes API server IPs (10.96.0.1/32, 192.168.49.2/32) over TCP port 443.

### MANIFESTS OF CLUSTER (in "k8s/01-kyverno.yaml" file)
-   **Audit Pod Security Restricted**
    -   Audits Pods in the xray-api namespace to ensure they follow restricted security best practices:
            -   Require seccompProfile set to RuntimeDefault.
            -   Containers must run as non-root, drop all Linux capabilities, disallow privilege escalation, and use a read-only root filesystem.
            -   Enforce that every container defines CPU/memory requests and limits.
            -   Disallow usage of host namespaces (hostNetwork, hostPID, hostIPC).
            -   Forbid usage of hostPath volumes.
-   **Service Account Automount Disabled**
    -   Enforces that Pods in the xray-api namespace disable automatic mounting of service account tokens.
    -   Excludes Pods labeled with app: xray-operator so the operator can continue functioning.
-   **Disallow Latest Tag**
    -   Enforces that Pods in the xray-api namespace cannot use the :latest tag for images.
    -   Applies this rule to containers, initContainers, and ephemeralContainers.
-   **Require Semantic Version-like Tags**
    -   Enforces that all images use numeric semantic version-like tags __(:X, :X.Y, or :X.Y.Z)__.
    -   Denies Pods using :latest, untagged images, or non-numeric tags.
    -   Applies consistently to containers, initContainers, and ephemeralContainers.
-   **Restrict Image Registries**
    -   Audits Pods in the xray-api namespace to ensure images are only pulled from approved registries.
    -   Allowed sources include:
        -   docker.io/* for team images.
        -   localhost:5000/* for local development images.
        -   postgres:* for PostgreSQL official images.