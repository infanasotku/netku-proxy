{{- define "common.deployment" -}}
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "common.fullname" . }}
  labels:
    infanasotku.com: "Infanasotku software engineier"

spec:
  replicas: {{ .Values.replicaCount | default 1 }}
  selector:
    matchLabels:
      app: {{ .Values.container.name }}

  template:
    metadata:
      labels:
        app: {{ .Values.container.name }}
        environment: {{ .Values.environment }}
      annotations:
        timestamp: {{ now | quote }}

    spec:
      runAsNonRoot: {{ .Values.securityContext.runAsNonRoot }}
      runAsUser: {{ .Values.securityContext.runAsUser }}

      containers:
        - name: {{ .Values.container.name }}
          image: {{ .Values.container.image }}:{{ .Values.container.tag }}
          imagePullPolicy: Always

          command: ["uvicorn"]
          args: {{ .Values.container.args | toJson }}
          ports:
            - containerPort: {{ .Values.container.port }}

          envFrom:
            - configMapRef:
                name: {{ include "common.fullname" . }}
            - secretRef:
                name: {{ include "common.fullname" . }}

          {{- with .Values.livenessProbe }}
          livenessProbe:
            {{- toYaml . | nindent 12 }}
          {{- end }}

          {{- with .Values.readinessProbe }}
          readinessProbe:
            {{- toYaml . | nindent 12 }}
          {{- end }}

          {{- with .Values.resources }}
          resources:
            {{- toYaml . | nindent 12 }}
          {{- end }}

          securityContext:
            capabilities:
              drop: ["ALL"]

      imagePullSecrets:
        - name: regcred
{{- end }}
