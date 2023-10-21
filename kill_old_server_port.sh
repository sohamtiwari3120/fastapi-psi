pidd="`ps aux | grep -v grep | grep fastapi_server | awk '{print $2}'`"
echo $pidd
kill -9 $pidd