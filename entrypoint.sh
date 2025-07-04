#!/bin/sh

chown -R $USR_NAME:$USR_GRPN .
exec runuser -u $USR_NAME "$@"