{{- define "common.secrets" -}}
apiVersion: v1
kind: Secret
metadata:
  name: {{ include "common.fullname" . }}
type: Opaque
stringData:
{{- $secrets := .Files.Get "temp-secrets.yaml" | fromYaml }}
{{- range $key, $val := $secrets }}
  {{ $key }}: {{ $val }}
{{- end }}
{{- end }}
