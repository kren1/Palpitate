CURRENT=`pwd`

SERVER=/home/app.py
CONTAINER_VIDEO=/home/server/Bill_Clinton.avi
CONTAINER_OPENCV=/opencv/

docker run -p 5000:5000 -v $CURRENT:/home/ palpitate-docker-image python $SERVER $CONTAINER_VIDEO $CONTAINER_OPENCV
#docker run -i -t -v $CURRENT:/home/ palpitate-docker-image /bin/bash

# -d flag tells docker to run image in the background
# -P flag tells docker to map container network ports to host
# run Palpitate docker image with command to start python server
