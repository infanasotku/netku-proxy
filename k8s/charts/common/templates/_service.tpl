{{- define "common.service" -}}
apiVersion: v1
kind: Service
metadata:
  name: {{ include "common.fullname" . }}
spec:
  type: ClusterIP
  selector:
    app: {{ .Values.container.name }}
  ports:
    - port: {{ .Values.container.port }}
      protocol: TCP
      targetPort: {{ .Values.container.port }}
{{- end }}
