#!/usr/bin/env bash
set -euo pipefail
SPEC_VERSION="${1:-1.0.0}"
SPEC="docs/api/openapi-${SPEC_VERSION}.yaml"
if [ ! -f "$SPEC" ]; then
  echo "Spec $SPEC not found" >&2
  exit 1
fi
JAR_VERSION=7.7.0
if [ ! -f openapi-generator-cli.jar ]; then
  curl -L "https://repo1.maven.org/maven2/org/openapitools/openapi-generator-cli/${JAR_VERSION}/openapi-generator-cli-${JAR_VERSION}.jar" -o openapi-generator-cli.jar
fi
rm -rf clients/python clients/typescript
java -jar openapi-generator-cli.jar generate -i "$SPEC" -g python -o clients/python --additional-properties=packageName=signet_protocol_client,packageVersion=${SPEC_VERSION}
java -jar openapi-generator-cli.jar generate -i "$SPEC" -g typescript-fetch -o clients/typescript --additional-properties=npmName=signet-protocol-client,npmVersion=${SPEC_VERSION}
echo "Clients generated under clients/ (python, typescript)."
