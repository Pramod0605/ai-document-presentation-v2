ssh -t administrator@69.197.145.4 'sudo docker logs -f $(sudo docker ps -q -f publish=5005)'
