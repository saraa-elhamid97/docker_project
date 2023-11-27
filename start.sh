#!/bin/bash
docker-compose up -d
#initiate replica set
sleep 10
docker exec -it docker_project_mongo1_1 mongosh --eval "rs.initiate({
 _id: \"myReplicaSet\",
 members: [
   {_id: 0, host: \"mongo1\"},
   {_id: 1, host: \"mongo2\"},
   {_id: 2, host: \"mongo3\"}
 ]
})"

ngrok http 8443 --domain=generally-fluent-sawfish.ngrok-free.app
