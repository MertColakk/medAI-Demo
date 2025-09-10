# OTHER PAGES (Click for navigate)
* [Kubernetes](./docs/kubernetes.md)
* [Security(Kyverno)](./docs/security.md)
* [Code Overviews](./docs/code.md)

# CONTENTS
* [Project Description](#project-description)
* [Install & Run](#install--run)
    
## PROJECT DESCRIPTION
This project is a Kubernetes-native application that integrates machine learning, API services, and database management into a secure and scalable platform.
At its core, the system uses Python (3.10+) to run an API service built with Flask and Flask-SQLAlchemy, backed by a PostgreSQL database for persistent storage. 
The API leverages TensorFlow/Keras and Pillow for image processing and machine learning tasks, enabling intelligent data analysis and predictions.
Deployment and scaling are handled via Docker and Kubernetes, ensuring portability and resilience across environments. Advanced security and compliance are enforced using Kyverno policies, which validate, mutate, and audit Kubernetes manifests to meet strict security standards.
For Kubernetes-native automation, the project employs the kopf operator framework alongside the official kubernetes Python client, enabling custom resource management and seamless integration with the cluster.
Together, these technologies provide a full-stack solution for building, running, and securing modern AI-driven applications.

### TECHNOLOGIES WHICH ARE USED
    -   PostgreSQL
    -   Python
    -   Kyverno
    -   Docker
    -   Kubernetes
    -   Python 3.10

### PYTHON LIBRARIES WHICH ARE USED
    -   Tensorflow / Keras
    -   Pillow
    -   Flask / Flask-SQLAlchemy
    -   psycopg2
    -   kopf
    -   kubernetes

## INSTALL & RUN
```bash
# Start installation
chmod +x manage.sh # (Only for the first time)
          and   

./manage.sh --install 
          or
./manage.sh -i 

# Start service (local)
python3 manage.sh --run
          or
python3 manage.sh -r

# Access into database (Optional)
python3 manage.sh --database
          or
python3 manage.sh -d

# Need help?
python3 manage.sh --help
          or
python3 manage.sh -h
```