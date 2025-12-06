{{- define "common.fullname" -}}
{{ printf "%s-%s" .Release.Name (.Values.environment | default "") | trunc 63 | trimSuffix "-" }}
{{- end }}

