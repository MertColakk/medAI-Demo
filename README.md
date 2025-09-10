# OTHER PAGES (Click for navigate)
* [Kubernetes](./docs/kubernetes.md)
* [Security with Kyverno](./docs/security.md)
* [Code Overviews](./docs/code.md)

# CONTENTS
* [Project Description](#project-description)
* [Install & Run](#install--run)
* [To Do](#todo)
    
## PROJECT DESCRIPTION
### TECHNOLOGIES WHICH ARE USED
    -   PostgreSQL
    -   Python
    -   Kyverno
    -   Docker
    -   Kubernetes
    -   Python 3.10+

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

## TODO
    -   Argo CD Kyverno Self Heal (STATUS: NOT STARTED)
    -   Argo CD Kyverno Secret Storage (STATUS: NOT STARTED)