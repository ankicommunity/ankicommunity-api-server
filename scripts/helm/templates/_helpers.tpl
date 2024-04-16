{{/*
Expand the name of the chart.
*/}}
{{- define "djankiserv.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "djankiserv.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "djankiserv.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "djankiserv.labels" -}}
helm.sh/chart: {{ include "djankiserv.chart" . }}
{{ include "djankiserv.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Common labels static
*/}}
{{- define "djankiserv.static.labels" -}}
helm.sh/chart: {{ include "djankiserv.chart" . }}
{{ include "djankiserv.static.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "djankiserv.selectorLabels" -}}
app.kubernetes.io/name: {{ include "djankiserv.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Selector labels static
*/}}
{{- define "djankiserv.static.selectorLabels" -}}
app.kubernetes.io/name: {{ include "djankiserv.name" . }}-static
app.kubernetes.io/instance: {{ .Release.Name }}-static
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "djankiserv.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "djankiserv.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Other functions added after the template
FIXME: this doesn't work for some reason...
*/}}
{{- define "djankiserv.publichosts" -}}
{{- join "," .Values.djankiserv.hosts }}
{{- end -}}
