kubectl -n xray-api get pods -l app=postgres
kubectl -n xray-api exec -it postgres-0 -- bash
psql -U $POSTGRES_USER -d $POSTGRES_DB