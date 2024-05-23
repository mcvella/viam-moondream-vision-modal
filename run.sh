#!/bin/bash
cd `dirname $0`

if [ -f .installed ]
  then
    source viam-env/bin/activate
  else
    python3 -m pip install --user virtualenv --break-system-packages
    python3 -m venv viam-env
    source viam-env/bin/activate
    pip3 install --no-cache --upgrade -r requirements.txt
    # we do this as there is a currently a grpclib version conflict between modal and viam-sdk
    pip3 install --no-cache modal
    modal token set --token-id $MODAL_TOKEN_ID --token-secret $MODAL_TOKEN_SECRET
    modal deploy modal_setup.py
    if [ $? -eq 0 ]
      then
        touch .installed
    fi
fi

# Be sure to use `exec` so that termination signals reach the python process,
# or handle forwarding termination signals manually
exec python3 -m src $@
