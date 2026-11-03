# Business 클러스터 설치

상위 개요와 현재 values 기준 절차는 저장소 루트 [README.md](../README.md)에 있습니다. 이 문서는 원래의 설치 순서를 유지합니다.

# **0. 사전 준비**

- 네임스페이스 생성

```
kubectl create ns monitoring      # 그라파나, 프로메테우스, 로키가 배포될 네임스페이스
kubectl create ns minio           # Loki, Tempo 데이터가 저장될 MinIO 가 배포될 네임스페이스
kubectl create ns tempo           # Tempo-distributed 컴포넌트들이 배포 될 네임스페이스
kubectl create ns otel-trace      # OpenTelemetry Collector 가 배포 될 네임스페이스
kubectl create ns test            # 샘플 어플리케이션이 올라갈 네임스페이스
```

---

- `2. biz` 디렉토리 구성은 아래와 같으며 번호 순서대로 설치를 진행하시면 됩니다.

```
cd 2.biz ; ll
drwxr-xr-x 4 root root 4096 May 21 14:30 1.minio/
drwxr-xr-x 4 root root 4096 May 21 09:45 2.kube-prometheus-stack/
drwxr-xr-x 4 root root 4096 May 20 12:35 3.promtail/
drwxr-xr-x 4 root root 4096 May 20 16:55 4.loki-distriuted/
drwxr-xr-x 5 root root 4096 May 21 14:27 5.tempo-distributed/
drwxr-xr-x 3 root root 4096 May 21 14:28 6.OpenTelemetry/
```

---

# **1. MinIO Install**

## **1-1. Minio secret 생성 ( Biz → Mgmt Minio 용도 )**

- 🔐 `minio-key.yaml` 파일 내용 설명

```
cat minio-key.yaml
type: s3
config:
  bucket: thanos
  endpoint: 203.0.113.10:32000# Bastion Public IP : NodePort
  access_key: CHANGE_ME_MINIO_CREDENTIAL
  secret_key: CHANGE_ME_MINIO_CREDENTIAL
  insecure:true
  signature_version2:true
```

- ✅ 이 설정은 **Biz** 의 object storage backend로 **Mgmt** 의 **MinIO**를 사용하기 위한 설정입니다.

```
kubectl create secret generic thanos-minio-secret -n monitoring --from-file=minio-key.yaml
```

- 생성 확인

```
kubectl get secrets | grep thanos
thanos-minio-secret       Opaque         1      47d      # secret generic 생성
```

## **1-2. Minio Pod 배포 [ Biz 용 Object Storage ( Loki,Tempo ) ]**

- persistence: storageClass: “수정”
- node label 지정 : `kubectl label nodes [NodeName] key=value`

```
persistence:
  ## @param persistence.enabled Enable MinIO&reg; data persistence using PVC. If false, use emptyDir
  enabled: true
  storageClass: "수정"
provisioning:
  nodeSelector:
    minio: "true"
```

```
~/backup/platform-monitoring/2.biz/1.minio# helm install minio . -n minio
```

- 배포 확인

```
kubectl get all -n minio
NAME                         READY   STATUS    RESTARTS   AGE
pod/minio-856d97c98c-lm7zd   1/1     Running   0          47h
NAME            TYPE       CLUSTER-IP   EXTERNAL-IP   PORT(S)                         AGE
service/minio   NodePort   10.10.0.97   <none>        9000:31000/TCP,9001:31002/TCP   47h
NAME                    READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/minio   1/1     1            1           47h
NAME                               DESIRED   CURRENT   READY   AGE
replicaset.apps/minio-856d97c98c   1         1         1       47h
```

## **1-3. Biz HAProxy 설정 ( MinIO )**

```
# MGMT MINIO(METRICS) Web Console ######################################
listen minio-api
  bind *:32000
  mode tcp
  server k8s-master01 192.168.10.11:32000  check inter 2000 rise 2 fall 5
  server k8s-master02 192.168.10.12:32000  check inter 2000 rise 2 fall 5
  server k8s-master03 192.168.10.13:32000  check inter 2000 rise 2 fall 5
  server k8s-worker01 192.168.10.21:32000  check inter 2000 rise 2 fall 5
  server k8s-worker02 192.168.10.22:32000  check inter 2000 rise 2 fall 5
  server k8s-worker03 192.168.10.23:32000  check inter 2000 rise 2 fall 5
listen minio-console
  bind *:32001
  mode tcp
  server k8s-master01 192.168.10.11:32001  check inter 2000 rise 2 fall 5
  server k8s-master02 192.168.10.12:32001  check inter 2000 rise 2 fall 5
  server k8s-master03 192.168.10.13:32001  check inter 2000 rise 2 fall 5
  server k8s-worker01 192.168.10.21:32001  check inter 2000 rise 2 fall 5
  server k8s-worker02 192.168.10.22:32001  check inter 2000 rise 2 fall 5
  server k8s-worker03 192.168.10.23:32001  check inter 2000 rise 2 fall 5
#########################################################################
```

- 콘솔 접속 확인
    - [[ BIZ ] MINIO_Console](http://203.0.113.10:31002/browser) : `Default Bucket : k8s-Loki, k8s-Tempo`

가이드가 참조하는 콘솔 캡처 `image-20250521-075631.png` 는 이 저장소에 포함되어 있지 않습니다.

---

# **2. kube-prometheus-stack Install**

- `kube-prometheus-stack : kube-prometheus-stack-66.4.0`

## **2-1. Values.yaml 수정**

- persistence: storageClass: “수정”
- node label 지정 : `kubectl label nodes [NodeName] monitoring=true`
- kubeEtcd: endpoints: `“masterIP 수정”`

```
grafana:
  persistence:
    enabled: true
    type: sts
    storageClassName: "수정"
    accessModes:
      - ReadWriteOnce
    size: 20Gi
    finalizers:
      - kubernetes.io/pvc-protection
prometheusSpec:
    nodeSelector:
      monitoring: "true"
kubeEtcd:
  enabled: true
  ## If your etcd is not deployed as a pod, specify IPs it can be found on
  endpoints:
   - 10.10.0.101
   - 10.10.0.102
   - 10.10.0.103
```

## **2-2. Prometheus-stack helm install**

```
~/backup/platform-monitoring/2.biz/2.kube-prometheus-stack# helm install prometheus . -n monitoring
```

- 배포 확인

```
kubectl get pods -n monitoring
NAME                                                     READY   STATUS    RESTARTS   AGE
alertmanager-prometheus-kube-prometheus-alertmanager-0   2/2     Running   0          7d22h
prometheus-grafana-0                                     3/3     Running   0          28h
prometheus-kube-prometheus-operator-67547cc956-gm86t     1/1     Running   0          7d22h
prometheus-kube-state-metrics-66f5694654-mswhn           1/1     Running   0          7d22h
prometheus-prometheus-kube-prometheus-prometheus-0       3/3     Running   0          7d22h
prometheus-prometheus-kube-prometheus-prometheus-1       3/3     Running   0          7d22h
prometheus-prometheus-node-exporter-9ns6f                1/1     Running   0          7d22h
prometheus-prometheus-node-exporter-hc7tv                1/1     Running   0          7d22h
prometheus-prometheus-node-exporter-kp6jq                1/1     Running   0          7d22h
prometheus-prometheus-node-exporter-sf6t5                1/1     Running   0          7d22h
prometheus-prometheus-node-exporter-vp8rg                1/1     Running   0          7d22h
prometheus-prometheus-node-exporter-wjjqq                1/1     Running   0          7d22h
kubectl get svc -n monitoring | grep NodePort
prometheus-grafana                            NodePort    10.10.0.174   <none>        80:32222/TCP                      7d22h
prometheus-kube-prometheus-prometheus         NodePort    10.10.0.128   <none>        9090:32221/TCP,8080:31531/TCP     7d22h
prometheus-kube-prometheus-thanos-discovery   NodePort    10.10.0.36    <none>        10901:30901/TCP,10902:30902/TCP   7d22h
thanos-query-frontend                         NodePort    10.10.0.176   <none>        9090:32223/TCP                    2d4h
```

## **2-3. Biz HAProxy 설정 ( Prometheus, Grafana )**

- `Grafana NodePort` : `32224`
- `Prometheus NodePort` : `30090`

```
# BIZ Prometheus,Grafana Console ########################################
listen biz-Grafana
  bind *:32224
  mode http
  server biz-master01 192.168.10.111:32224  check inter 2000 rise 2 fall 5
  server biz-master02 192.168.10.112:32224  check inter 2000 rise 2 fall 5
  server biz-master03 192.168.10.113:32224  check inter 2000 rise 2 fall 5
  server biz-worker01 192.168.10.121:32224  check inter 2000 rise 2 fall 5
  server biz-worker02 192.168.10.122:32224  check inter 2000 rise 2 fall 5
  server biz-worker03 192.168.10.123:32224  check inter 2000 rise 2 fall 5
listen biz-prometheus
  bind *:30090
  mode http
  server biz-master01 192.168.10.111:30090  check inter 2000 rise 2 fall 5
  server biz-master02 192.168.10.112:30090  check inter 2000 rise 2 fall 5
  server biz-master03 192.168.10.113:30090  check inter 2000 rise 2 fall 5
  server biz-worker01 192.168.10.121:30090  check inter 2000 rise 2 fall 5
  server biz-worker02 192.168.10.122:30090  check inter 2000 rise 2 fall 5
  server biz-worker03 192.168.10.123:30090  check inter 2000 rise 2 fall 5

```

---

# **3. Promtail Install**

- `Chart Version : promtail-6.16.6`
- Promtail Helm 배포

```
~/backup/platform-monitoring/2.biz/3.promtail# helm install promtail . -n monitoring
```

---

# **4. Loki-distributed Install**

- `Chart Version : loki-distributed-0.80.2`

## **4-1. Values.yaml 수정**

- persistence: storageClass: “수정”
- node label 지정 : `kubectl label nodes [NodeName] monitoring=true`

```
ingester:
  persistence:
    # -- Enable creating PVCs which is required when using boltdb-shipper
    enabled: true
        storageClass: "수정"
indexGateway:
  persistence:
    # -- Enable creating PVCs which is required when using boltdb-shipper
    enabled: true
        storageClass: "수정"
distributor:
  nodeSelector:
    monitoring: "true"
querier:
  nodeSelector:
    monitoring: "true"
query-frontend:
  nodeSelector:
    monitoring: "true"
```

- Loki Distributed Helm 배포

```
~/backup/platform-monitoring/2.biz/4.loki-distriuted# helm install loki . -n monitoring
```

- 아래와 같이 `loki-loki-distributed-gateway 서비스가 노드포트로 설정이 되어 있어야 됩니다. (MGMT Grafana 에서 BIZ Loki Datasource 연결하기 위함)`

```
loki-loki-distributed-gateway                   NodePort    10.10.0.75    <none>        80:31231/TCP                      47h
```

## **4-2. Biz HAProxy 설정 (Bastion)**

```
# BIZ Loki-distributed-querier ###########################################
listen loki-loki-distributed-querier
  bind *:31231
  mode tcp
  server biz-master01 192.168.10.111:31231  check inter 2000 rise 2 fall 5
  server biz-master02 192.168.10.112:31231  check inter 2000 rise 2 fall 5
  server biz-master03 192.168.10.113:31231  check inter 2000 rise 2 fall 5
  server biz-worker01 192.168.10.121:31231  check inter 2000 rise 2 fall 5
  server biz-worker02 192.168.10.122:31231  check inter 2000 rise 2 fall 5
  server biz-worker03 192.168.10.123:31231  check inter 2000 rise 2 fall 5
```

## **4-3. Grafana DataSource 연결**

- [BIZ] Grafana Loki DataSource : `http://loki-loki-distributed-gateway:80`
- [MGMT] Grafana Loki DataSource : `http://203.0.113.10:31231`

---

# **5. Tempo-distributed Install**

- `Chart Version : tempo-distributed-1.32.2`

## **5-1. Values.yaml 수정**

- persistence: storageClass: “수정”
- node label 지정 : `kubectl label nodes [NodeName] monitoring=true`

```
metricsGenerator:
  persistence:
    # -- Enable creating PVCs which is required when using boltdb-shipper
    enabled: true
    storageClass: "수정"
ingester:
  persistence:
  # -- Enable creating PVCs which is required when using boltdb-shipper
  enabled: true
  storageClass: "수정"
```

- Tempo Distributed Helm 배포

```
~/backup/platform-monitoring/2.biz/5.tempo-distributed# helm install tempo . -n tempo
```

- 아래와 같이 `tempo-gateway 서비스가 노드포트로 설정이 되어 있어야 됩니다. (MGMT Grafana 에서 BIZ Tempo Datasource 연결하기 위함)`

```
tempo-gateway                       NodePort    10.10.0.120   <none>        80:31538/TCP                                    9m48s
```

## **5-2. Biz HAProxy 설정 (Bastion)**

```
# BIZ tempo-distributed ##########
listen tempo-query-frontend
  bind *:31538
  mode tcp
  server biz-master01 192.168.10.111:31538  check inter 2000 rise 2 fall 5
  server biz-master02 192.168.10.112:31538  check inter 2000 rise 2 fall 5
  server biz-master03 192.168.10.113:31538  check inter 2000 rise 2 fall 5
  server biz-worker01 192.168.10.121:31538  check inter 2000 rise 2 fall 5
  server biz-worker02 192.168.10.122:31538  check inter 2000 rise 2 fall 5
  server biz-worker03 192.168.10.123:31538  check inter 2000 rise 2 fall 5
```

## **5-3. Grafana DataSource 연결**

- [BIZ] Grafana Tempo DataSource : `http://tempo-query-frontend-discovery.tempo:3100`
- [MGMT] Grafana Tempo DataSource : `http://203.0.113.10:31538`

---

# **6. OpenTelemetry Install**

- 번호 순서대로 순차적으로 배포 합니다.

```
-rw-r--r-- 1 root root 986843 Oct  9  2024 1.cert-manager.yaml
-rw-r--r-- 1 root root 701222 May  9 15:26 2.opentelemetry-operator.yaml
-rw-r--r-- 1 root root   4473 May 21 12:37 3.OpenTelemetryCollector.yaml
-rw-r--r-- 1 root root    602 May  9 15:26 4.otel-collector-spanmetrics.yaml
drwxr-xr-x 2 root root   4096 May 23 09:45 5.instrumentations/
drwxr-xr-x 3 root root   4096 May 21 13:45 sample-application/
```

## **6-1. Cert-Manager Install**

- cert-manager는 Let's Encrypt 같은 인증 기관(CA)과 통신하여 **TLS 인증서를 자동 발급하고 갱신**해주는 Kubernetes용 컨트롤러입니다.

```
kubectl apply -f 1.cert-manager.yaml
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.16.1/cert-manager.yaml
```

```
kubectl get pods -n cert-manager
NAME                                      READY   STATUS    RESTARTS       AGE
cert-manager-cainjector-fb79858b4-5ssb4   1/1     Running   18 (37h ago)   2d16h
cert-manager-fbbb9fdd5-tsmcb              1/1     Running   12 (37h ago)   2d16h
cert-manager-webhook-6cc5985dd5-kjx6h     1/1     Running   1 (18h ago)    2d16h
```

## **6-2. OpenTelemetry Operator Install**

- **OpenTelemetry Collector**, **Auto-instrumentation**, **CustomResource 관리**를 자동화해주는 Kubernetes 오퍼레이터입니다.

```
kubectl apply -f 2.opentelemetry-operator.yaml
kubectl apply -f https://github.com/open-telemetry/opentelemetry-operator/releases/latest/download/opentelemetry-operator.yaml
```

```
kubectl get pods -n opentelemetry-operator-system
NAME                                                         READY   STATUS    RESTARTS       AGE
opentelemetry-operator-controller-manager-867cbbd5d4-gl6l4   2/2     Running   15 (37h ago)   2d17h
```

## **6-3. OpenTelemetry Collector Install**

- **OpenTelemetry Collector**는 다양한 형식의 telemetry 데이터(로그, 메트릭, 트레이스)를 수집·변환·전송하는 벤더 중립적인 파이프라인 컴포넌트입니다.

```
~/backup/platform-monitoring/2.biz/6.OpenTelemetry# kubectl apply -f 3.OpenTelemetryCollector.yaml
```

```
~/backup/platform-monitoring/2.biz/6.OpenTelemetry# kubectl get pods -n otel-trace
NAME                                   READY   STATUS    RESTARTS      AGE
collector-collector-668d99875b-x6phg   1/1     Running   1 (18h ago)   45h
```

## **6-4. OpenTelemetry SpanMetrics Install**

- **Prometheus Operator용** `ServiceMonitor` 리소스로, OpenTelemetry Collector의 **SpanMetrics** 메트릭을 수집하기 위한 설정입니다.

```
kubectl apply -f 4.otel-collector-spanmetrics.yaml
```

```
kubectl get servicemonitors.monitoring.coreos.com  -n otel-trace
NAME                         AGE
otel-collector-spanmetrics   2d17h
```

## **6-5. Auto-Instrument**

- 개발 언어에 맞게 선택적으로 배포 합니다.

```
-rw-r--r-- 1 root root  661 May  9 15:26 java-instrument.yaml
-rw-r--r-- 1 root root  372 May 21 14:20 python-instrument.yaml
```

```
kubectl get instrumentations.opentelemetry.io -n test
NAME                     AGE   ENDPOINT                                                       SAMPLER   SAMPLER ARG
python-instrumentation   44h   http://collector-collector.otel-trace.svc.cluster.local:4318
```

- Auto-Instrument를 적용할 테스트 파드는 아래와 같습니다.

```
kubectl get pods -n test
platform-multicluster-app-7c8678b5c7-hctt6   1/1     Running   0          15h
```

- spec: template: metadata: annotations: 아래 두줄 삽입

```
        instrumentation.opentelemetry.io/inject-python: "true"
        instrumentation.opentelemetry.io/python-container-names: api
```

- 적용 확인

```
kubectl describe pods platform-multicluster-app-7c8678b5c7-hctt6
Name:             platform-multicluster-app-7c8678b5c7-hctt6
Namespace:        test
...
Annotations:      instrumentation.opentelemetry.io/inject-python: true
                  instrumentation.opentelemetry.io/python-container-names: api
Status:           Running
IP:               100.100.3.3
IPs:
  IP:           100.100.3.3
Controlled By:  ReplicaSet/platform-multicluster-app-7c8678b5c7
...
Init Containers:
  opentelemetry-auto-instrumentation-python:
    Container ID:  containerd://08fe1c92485e04f7b31ce1a176af7f56874978688037911a8674dace25fb7828
    Image:         ghcr.io/open-telemetry/opentelemetry-operator/autoinstrumentation-python:0.53b1
    Image ID:      ghcr.io/open-telemetry/opentelemetry-operator/autoinstrumentation-python@sha256:1fe31f53171ffaa5eb8267ba4ba481197bb186821caec2d711a4697bf05550b0
    Port:          <none>
    Host Port:     <none>
...
Containers:
  api:
    Container ID:   containerd://d788fa9b9d16c0a8c448f771ab35c9f005daa53343caeee49b763ea7211d6734
    Image:          lbg3977/platform-multicluster-app
    Image ID:       docker.io/lbg3977/platform-multicluster-app@sha256:5319211c1189e42625de52942700a7fbd9a0cc4870b00ce2064ef6a17732e2b9
    Port:           3000/TCP
    Host Port:      0/TCP
    State:          Running
      Started:      Thu, 22 May 2025 19:02:17 +0900
    Ready:          True
    Restart Count:  0
    Environment:
      OTEL_NODE_IP:                                       (v1:status.hostIP)
      OTEL_POD_IP:                                        (v1:status.podIP)
      PYTHONUNBUFFERED:                                  1
      API_HOST:                                          0.0.0.0
      API_PORT:                                          3000
      OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED:  true
      PYTHONPATH:                                        /otel-auto-instrumentation-python/opentelemetry/instrumentation/auto_instrumentation:/otel-auto-instrumentation-python
      OTEL_EXPORTER_OTLP_PROTOCOL:                       http/protobuf
      OTEL_TRACES_EXPORTER:                              otlp
      OTEL_METRICS_EXPORTER:                             otlp
      OTEL_LOGS_EXPORTER:                                otlp
      OTEL_SERVICE_NAME:                                 platform-multicluster-app
      OTEL_EXPORTER_OTLP_ENDPOINT:                       http://collector-collector.otel-trace.svc.cluster.local:4318
      OTEL_RESOURCE_ATTRIBUTES_POD_NAME:                 platform-multicluster-app-7c8678b5c7-hctt6 (v1:metadata.name)
      OTEL_RESOURCE_ATTRIBUTES_NODE_NAME:                 (v1:spec.nodeName)
      OTEL_PROPAGATORS:                                  tracecontext,baggage
      OTEL_RESOURCE_ATTRIBUTES:                          k8s.container.name=api,k8s.deployment.name=platform-multicluster-app,k8s.namespace.name=test,k8s.node.name=$(OTEL_RESOURCE_ATTRIBUTES_NODE_NAME),k8s.pod.name=$(OTEL_RESOURCE_ATTRIBUTES_POD_NAME),k8s.replicaset.name=platform-multicluster-app-7c8678b5c7,service.instance.id=test.$(OTEL_RESOURCE_ATTRIBUTES_POD_NAME).api,service.namespace=test
    Mounts:
      /app/logs from logs (rw)
      /home/appuser/.kube from kubeconfig (ro)
      /otel-auto-instrumentation-python from opentelemetry-auto-instrumentation-python (rw)
      /var/run/secrets/kubernetes.io/serviceaccount from kube-api-access-lrqps (ro)
```

- 해당 파드 내에 `otel-auto-instrumentation-python` Agent 파일 확인

```
kubectl exec -it platform-multicluster-app-7c8678b5c7-hctt6 -- sh
Defaulted container "api" out of: api, opentelemetry-auto-instrumentation-python (init)
appuser@platform-multicluster-app-7c8678b5c7-hctt6:/$ ls
app  bin  boot  dev  etc  home  lib  lib64  media  mnt  opt  otel-auto-instrumentation-python  proc  root  run  sbin  srv  sys  tmp  usr  var
```

---
