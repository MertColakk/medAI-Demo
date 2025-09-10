# OTHER PAGES (Click for navigate)
* [Main Page](../README.md)
* [Kubernetes](./kubernetes.md)
* [Code Overviews](./code.md)

# CONTENTS
* [Support Materials](#support-materials-about-kyverno)
* [Pod Security Standards](#pod-security-standards)
* [Security Architecture](#security-architecture)
* [Kyverno Overview](#kyverno-overview)
* [Kyverno Workflow](#kyverno-workflow)
* [Kyverno Manifest Implementations](#kyverno-manifest-implementations)
* [Advantages and Limitations of Kyverno](#advantages-and-limitations-of-kyverno)

---

## SUPPORT MATERIALS ABOUT KYVERNO

### General
#### 1. Kubernetes Admission Workflow with Kyverno
![Kyverno Workflow](https://kyverno.io/images/kubernetes-admission-controllers.png)

This diagram shows the **general Kubernetes admission control process** and how Kyverno fits into it.

* A developer submits a manifest (e.g., Pod, Deployment).
* The Kubernetes API server first performs basic schema validation.
* Then, **admission controllers** (like Kyverno) evaluate policies.
* Based on the result, the request is either **admitted, rejected, or audited**.

Kyverno acts as a **Validating and Mutating Admission Webhook**, enforcing security, governance, and best practices directly in the cluster.

---

#### 2. JSON Validation Flow in Kyverno
![Kyverno Workflow Basic Explanation](https://neonmirrors.net/images/2023-07/experimental-generic-json-validation-with-kyverno/json-flow.png)

This diagram breaks down the **admission webhook evaluation process**:

* User request → Kubernetes API server → Kyverno webhook.
* Kyverno parses the request JSON and applies policy rules.
* If rules fail in enforce mode → request is denied.
* If rules are in audit mode → request passes, but a violation is logged.

This highlights how Kyverno works **with raw JSON manifests** and applies its policy logic directly on Kubernetes resources.

---

#### 3. Kyverno Policy Management Lifecycle
![Policy Management](https://miro.medium.com/v2/resize\:fit:1200/0*6fKcb22njWeWcwnu.png)

This image explains the **policy management lifecycle**:
* **Define**: Policies are written in YAML (`ClusterPolicy`, `Policy`).
* **Distribute**: Applied via GitOps or kubectl.
* **Enforce / Audit**: Kyverno applies rules on admission or background scans.
* **Report**: Violations are logged into `PolicyReports` and can be integrated into dashboards (e.g., Prometheus, Grafana, SIEM).

It shows that Kyverno policies are **living documents** — continuously enforced and reported.

---

### Controllers
#### 4. Admission Controller Phases
![Admission Controller Phases](https://cdn.thenewstack.io/media/2023/05/d88945c4-image1a.jpg)

Kyverno consists of **multiple controllers**, each handling a specific responsibility:
* **Admission Controller**: Handles real-time admission requests (`validate`, `mutate`, `verifyImage`).
* **Background Controller**: Applies policies to existing resources in the cluster.
* **Cleanup Controller**: Deletes resources based on conditions (e.g., TTL).
* **Reports Controller**: Collects violation results into PolicyReports.

This diagram shows how Kyverno runs as **a set of controllers**, not just a single webhook.

---

#### 5. Cleanup and Temporary Policy Architecture
![Cleanup Policy and Temporary Policy](https://neonmirrors.net/images/2023-02/policy-exception-expiration/architecture.png)

This architecture diagram explains **Kyverno’s Cleanup Policies and Policy Exceptions**:
* Policies can have **time-based lifecycles** (e.g., expire after 24h).
* This is useful for **temporary exceptions** — e.g., allowing a developer to bypass a policy just for debugging.
* The **Cleanup Controller** automatically removes expired exceptions.

This ensures that **temporary policies don’t become permanent security gaps**.

---

### Policies
#### 6. Policy and Rule Structure
![Policy and Rules](https://release-1-12-0.kyverno.io/images/Kyverno-Policy-Structure.png)

A Kyverno policy is composed of:
* **Policy (ClusterPolicy / Policy)** → top-level object.
* **Rules** → each rule targets certain resources and applies validation, mutation, generation, or verification.
* **Match / Exclude** → define what resources the rule applies to.
* **Validate / Mutate / Generate** → actions to take.

- Validate
  Validation policies check Kubernetes resources against defined rules.
    Example: Ensure all Pods run as non-root, or forbid the use of :latest image tags.
- Modes:
  - Audit → Logs the violation but still admits the resource.
  - Enforce → Denies the request if it violates policy.
  - Mutate
    Mutation policies automatically modify resource manifests during admission.
    - Example: Add automountServiceAccountToken: false if it is not defined, or inject a default securityContext.
    - Ensures consistency without relying on developers to manually add every required field.
Generate
  Generation policies create or copy additional Kubernetes resources based on conditions.
  - Example: When a new Namespace is created, Kyverno can automatically generate a NetworkPolicy or a ResourceQuota.
  - Useful for default-deny, baseline security, and compliance automation.

This structure allows **fine-grained control** at both cluster and namespace level.

- **Comparison table about policy types:**
  - Validate
    - Purpose: Ensures resources comply with security and governance rules.
      Example Use Cases:
        - Deny Pods running as root.
        - Forbid use of :latest image tags.
      Effect on Resources:
        - In Audit mode: violation logged, resource still created.
        - In Enforce mode: resource is denied.
  - Mutate
    - Purpose: Automatically modifies manifests to meet policy requirements.
      Example Use Cases:
        - Add automountServiceAccountToken: false.
        - Inject default securityContext.
    Effect on Resources:
    - Resource is admitted, but fields are patched or added before creation.
  - Generate
    - Purpose: Creates or copies new resources automatically based on triggers.
      Example Use Cases:
      - Generate a NetworkPolicy when a Namespace is created.
      - Apply default ResourceQuota to new Namespaces.
      Effect on Resources:
      - Additional Kubernetes objects are created alongside the requested resource.                          |

- **Comparison table about policy modes:**
  - Audit
    - Purpose: Monitor and report violations without blocking resources.
    Behavior on Violation:
      - Resource is still created/updated.
      - Violation is logged in PolicyReport / ClusterPolicyReport.
    When to Use:
      - Testing new policies in staging.
      - Observing impact before enforcing.
      - Compliance reporting in production.
    Example: A Pod with ":latest"image is admitted but violation appears in reports.
  - Enforce
    - Purpose: Strictly enforce compliance by blocking non-conforming resources.
    Behavior on Violation:
      - Resource creation/update is denied.
      - Violation prevents resource admission.
    When to Use:
      - Production clusters with mature policies.
      - Critical security and compliance requirements.
    Example: A Pod with ":latest" image is rejected and not created.

---

#### 7. Verify Image Policy
![Verify Image Policy](https://release-1-9-0.kyverno.io/images/image-verify-rule.png)

This diagram explains **image verification policies**:
* Ensures images are signed (e.g. Cosign).
* Restricts what registries images can come from.
* Blocks use of untrusted or unsigned images.

This is critical for **supply chain security**, ensuring only verified container images are admitted.

---

#### 8. Mutation Policy
![Mutation Policy](https://miro.medium.com/v2/resize\:fit:1400/1*pga79LRRmVn2hgmpdYFj_A.png)

Mutation policies allow Kyverno to **patch manifests automatically**.
Examples:
* Add securityContext fields (`runAsNonRoot: true`).
* Set defaults (`automountServiceAccountToken: false`).
* Inject sidecars or labels.

This reduces human error — developers don’t need to remember every security field, Kyverno **fixes manifests automatically**.

---

#### 9. Report Policy
![Report Policy](https://higherlogicdownload.s3.amazonaws.com/IMWUC/UploadedImages/54MZ8FrRZ6bJincYApY0_Screenshot%202025-08-12%20at%204.56.17%E2%80%AFAM-L.png)

Kyverno generates **PolicyReports** and **ClusterPolicyReports** that summarize compliance:
* Show how many resources passed or failed each rule.
* Exportable to dashboards (Prometheus, Grafana, SIEM tools).
* Critical for **auditing, compliance, and security posture management**.

Reports help organizations **track drift and enforce standards at scale**.

---

## POD SECURITY STANDARDS
* **Namespace Level**
  * Containers must run as **non-root**.
  * **Privileged** containers are not permitted.
  * `hostPath` volumes are forbidden.
  * **AppArmor** profiles must be applied (default by Kubernetes).
  * **Seccomp** profiles must not be `unconfined` (Kubernetes defaults to `RuntimeDefault`).

---

## SECURITY ARCHITECTURE
### Local Security Layer
* Pod Security Admission (PSA) set to **restricted**.
* ValidatingAdmissionPolicies (VAP) monitor `CREATE` and `UPDATE` requests.
* Admission logging and filtering rules enabled.
* **etcd** encrypted.
* Anonymous access disabled and `NodeRestriction` enabled.

### Kyverno Layer
* Use `validationFailureAction: Enforce` with `failurePolicy: Fail` for critical rules.
* Exceptions managed through dedicated CRDs, RBAC, and TTL.
* Kyverno controllers deployed redundantly with anti-affinity and webhook timeout tuning.

### GitOps / Argo CD Layer 
Argo CD and Kyverno complement each other by combining declarative GitOps workflows with policy-driven security and compliance:
  - Self-Healing & Drift Correction
    - Argo CD continuously compares the live cluster state with the desired state stored in Git.
    - If a resource is changed manually (e.g., kubectl edit) or drifts due to automation bugs, Argo CD automatically reverts it back to the declared state.
    - This prevents configuration drift, a common problem in large clusters where resources slowly deviate from the intended design.
  - Policy-as-Code Enforcement with Kyverno
    - While Argo CD ensures the what (desired manifests are applied correctly), Kyverno enforces the how (those manifests meet security and compliance rules).
    - Example: Argo CD syncs a Deployment → Kyverno validates that containers don’t run as root, don’t use :latest tags, and apply proper seccomp profiles.
  - Defense Against Misconfigurations
    - Without Kyverno, Argo CD may sync insecure manifests (e.g., privileged containers).
    - Without Argo CD, Kyverno can enforce rules, but doesn’t guarantee drift correction or that desired manifests are restored if altered.
    - Together, they prevent both accidental and malicious misconfigurations from persisting in the cluster.
  - Compliance & Auditability
    - GitOps ensures all changes flow through Git → audit trail of who changed what, when, and why.
    - Kyverno produces PolicyReports, allowing organizations to prove compliance with security frameworks (CIS Benchmarks, NIST, PCI-DSS, etc.).
    - Combined, you gain both audit history and enforcement at runtime.
  - Operational Efficiency
    - Argo CD reduces manual ops by automating syncs and rollbacks.
    - Kyverno reduces human error by mutating manifests (e.g., auto-adding automountServiceAccountToken: false) instead of relying on developers.
    - Teams spend less time debugging misconfigurations and more time shipping features securely.

---

## KYVERNO OVERVIEW
**Kyverno** is a **Kubernetes-native policy engine**.
It allows teams to **validate, mutate, generate, verify, and clean up** Kubernetes resources using **YAML-based policies**

---

## KYVERNO WORKFLOW
```yaml
    User[Developer:kubectl apply Pod] --> API[Kubernetes API Server]
    API --> |Admission Request| Kyverno[Kyverno Admission Webhook]
    Kyverno --> |Check Rules| Policy[ClusterPolicy]
    Policy --> |Violation?| Decision{Permit or Deny}
    Decision --> |If Pass| Create[Pod Created]
    Decision --> |If Fail| Block[Request Denied]
    Decision --> |If Audit| Report[Violation logged in PolicyReport]
```

### Steps
1. **User Action**: Developer applies a manifest (egg., Pod).
2. **Kubernetes API Server**: Sends admission request to Kyverno.
3. **Kyverno Admission Webhook**: Evaluates against active policies.
4. **Policy Evaluation**: Rules are checked in order.
5. **Decision**:
   * Permit → Resource created.
   * Deny → Resource rejected.
   * Audit → Resource created, violation logged in `PolicyReport`.

---

## KYVERNO MANIFEST IMPLEMENTATIONS

### 1. Pod Security Policies

#### 1.1 Audit Pod Security Restricted
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: audit-pod-security-restricted
spec:
  validationFailureAction: Audit
  rules:
    - name: require-seccomp
      match: { resources: { kinds: ["Pod"], namespaces: ["xray-api"] } }
      validate:
        message: "Pods must use seccompProfile RuntimeDefault"
        pattern:
          spec:
            securityContext:
              seccompProfile:
                type: "RuntimeDefault"
          .
          .
          .
```
* **Purpose**: Audit Pods for compliance with security hardening.
* **Key Rules**:
  * Require `seccompProfile: RuntimeDefault`.
  * Enforce `runAsNonRoot`, `readOnlyRootFilesystem`, drop all capabilities.
  * Require CPU/memory limits.
  * Forbid host namespaces (`hostNetwork`, `hostPID`, `hostIPC`).
  * Forbid `hostPath` volumes.
* **Mode**: `Audit` → Violations logged, Pods still admitted.

---

### 2. Service Account Security

#### 2.1 Disable Automount of ServiceAccount Tokens
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: sa-automount-disabled
spec:
  validationFailureAction: Enforce
  rules:
    - name: pod-sa-automount
      match:
        resources: { kinds: ["Pod"], namespaces: ["xray-api"] }
      exclude:
        resources: { selector: { matchLabels: { app: xray-operator } } }
      mutate:
        patchStrategicMerge:
          spec:
            automountServiceAccountToken: false
```
* **Purpose**: Prevent token sprawl by disabling automatic service account token mounts.
* **Exclusion**: Operator Pods require tokens → excluded.
* **Mode**: `Enforce` → Violations denied.
* **Type**: `mutate` → Automatically patches Pod manifests.

---

### 3. Image Governance Policies

#### 3.1 Disallow Latest Tag
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: disallow-latest-tag
spec:
  validationFailureAction: Enforce
  rules:
    - name: no-latest-containers
      match: { resources: { kinds: ["Pod"], namespaces: ["xray-api"] } }
      validate:
        message: "Do not use :latest tags."
        pattern:
          spec:
            containers:
              - image: "!*:latest"
```
* **Purpose**: Prevent usage of `:latest` image tags.
* **Applies To**: containers, initContainers, ephemeralContainers.
* **Mode**: `Enforce`.

---

#### 3.2 Require Semantic Version-like Tags
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-semver-like-tags
spec:
  validationFailureAction: Enforce
  background: true
  rules:
    - name: containers-must-use-numeric-tags
      match: { any: [ { resources: { kinds: ["Pod"] } } ] }
      validate:
        message: "Images must use numeric tags."
        foreach:
          - list: "request.object.spec.containers[].image"
            deny:
              conditions:
                any:
                  - key: "{{ (split(element, ':'))[1] || '' }}"
                    operator: Equals
                    value: "latest"
```
* **Purpose**: Require explicit semantic version tags (`:X`, `:X.Y`, `:X.Y.Z`).
* **Rejects**: `:latest`, untagged, or non-numeric tags.
* **Mode**: `Enforce`.
* **Feature**: `foreach` iterates through container fields.

---

#### 3.3 Restrict Image Registries
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: restrict-image-registries
spec:
  validationFailureAction: Audit
  rules:
    - name: only-allowed-registries
      match: { resources: { kinds: ["Pod"], namespaces: ["xray-api"] } }
      validate:
        message: "Only allowed registries."
        anyPattern:
          - spec:
              containers:
                - image: "docker.io/*"
          - spec:
              containers:
                - image: "localhost:5000/*"
          - spec:
              containers:
                - image: "postgres:*"
```
* **Purpose**: Audit Pods that use images outside of approved registries.
* **Allowed Registries**:

  * `docker.io/*`
  * `localhost:5000/*`
  * `postgres:*`
* **Mode**: `Audit`.

---

## ADVANTAGES AND LIMITATIONS OF KYVERNO

### + Advantages
* **Versatile**: Supports validation, mutation, generation, image verification, and cleanup.
* **Audit-first approach**: Safe rollout with audit before enforcement.

### - Limitations
* **Performance**: Heavy use can increase admission latency in large clusters.
* **Webhook dependency**: If webhook is slow/unavailable → may block workloads (`Fail`) or silently pass (`Ignore`).
* **Registry reliance**: Image verification requires working external registries/signing tools.
* **Scaling**: Needs tuning of replicas, webhooks, and timeouts for multi-tenant or high-throughput clusters.