#!/usr/bin/env bash

ROOT_DIR="$(cd -- "$(dirname "$0")/../" >/dev/null 2>&1 ; pwd -P )"
STACK_NAME="uni-prop-local-web-api"

JSON_FILE="$ROOT_DIR/data/property_data.json"
echo "JSON_FILE: '${JSON_FILE}'"

DDB_TBL_NAME="$(aws cloudformation describe-stacks --stack-name ${STACK_NAME} --query 'Stacks[0].Outputs[?OutputKey==`UnicornWebTableName`].OutputValue' --output text)"
echo "DDB_TABLE_NAME: '${DDB_TBL_NAME}'"

echo "LOADING ITEMS TO DYNAMODB:"
aws ddb put ${DDB_TBL_NAME} file://${JSON_FILE}
echo "DONE!"
