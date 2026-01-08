#!/bin/bash
# SERVICE="api"
# TMP_SECRETS_PATH="charts/${SERVICE}/temp-secrets.yaml"

# sops -d deploy/secrets/test/common.secrets.yaml > "${TMP_SECRETS_PATH}"

# helm template netku-proxy-${SERVICE} ./charts/${SERVICE} \
#   -f deploy/values/common/${SERVICE}.values.yaml \
#   -f deploy/values/common/common.values.yaml \
#   -f deploy/values/test/common.values.yaml \
#   -f deploy/values/test/${SERVICE}.values.yaml \
#   --dependency-update \
#   --namespace netku-test
    
# # helm lint ./charts/${SERVICE}  \
# #  -f deploy/values/prod/common.values.yaml \
# #  -f deploy/values/prod/${SERVICE}.values.yaml \
# #  --namespace netku-prod
  
# rm -f "${TMP_SECRETS_PATH}"
# rm -f ./charts/${SERVICE}/Chart.lock
# rm -rf ./charts/${SERVICE}/charts

helmfile -f helmfile.yaml.gotmpl --state-values-set tag=test-tag -e test --skip-refresh -l svc=migration template
