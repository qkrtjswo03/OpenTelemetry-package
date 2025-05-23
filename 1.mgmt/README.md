# **1. MinIO Install**

## **1-1. 네임스페이스 생성**

```
kubectl create ns monitoring
kubectl create ns minio
```

## **1-2. Minio secret 생성**

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

- ✅ 이 설정은 **Thanos**의 object storage backend로 **MinIO**를 사용하기 위한 설정입니다.

```
kubectl create secret generic thanos-minio-secret -n monitoring --from-file=minio-key.yaml
```

- 생성 확인

```
kubectl get secrets | grep thanos
thanos-minio-secret       Opaque         1      47d      # secret generic 생성
```

## **1-3. Minio Pod 배포 [ Metrics 용도 ]**

- persistence: storageClass: “수정”
- node label 지정 : `kubectl label nodes [NodeName] key=value`

```
persistence:
  ## @param persistence.enabled Enable MinIO&reg; data persistence using PVC. If false, use emptyDir
  enabled: true
  storageClass: ""
nodeSelector:
  node: "infra"
```

```
~/backup/platform-monitoring/1.mgmt/1.minio# helm install minio . -n minio
```

- 배포 확인 ( `Pending 상태면 노드셀렉터 지정` )

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

## **1-4. MGMT HAProxy 설정 ( MinIO )**

- `Minio-API` : `32000`
- `Minio-Console` : `32001`

```
# MGMT MINIO(METRCICS) Web Console ######################################
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
    - [[MGMT] MINIO_Console](http://203.0.113.10:32001/browser)

Open image-20250521-062003.png

`Default Bucket : thanos`

---

# **2. kube-prometheus-stack Install**

- `kube-prometheus-stack : kube-prometheus-stack-66.4.0`

## **2-1. Values.yaml 수정**

- persistence: storageClass: “수정”

```
  persistence:
    enabled: true
    type: sts
    storageClassName: "수정"
    accessModes:
      - ReadWriteOnce
    size: 20Gi
    finalizers:
      - kubernetes.io/pvc-protection
```

## **2-2. Prometheus-stack helm install**

```
~/backup/platform-monitoring/1.mgmt/2.kube-prometheus-stack# helm install prometheus . -n monitoring
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

## **2-3. MGMT HAProxy 설정 ( Prometheus, Grafana )**

- `Grafana NodePort` : `32222`
- `Prometheus NodePort` : `32221`

```
# MGMT Prometheus,Grafana Console #######################################
listen mgmt-grafana
  bind *:32222
  mode http
  server k8s-master01 192.168.10.11:32222  check inter 2000 rise 2 fall 5
  server k8s-master02 192.168.10.12:32222  check inter 2000 rise 2 fall 5
  server k8s-master03 192.168.10.13:32222  check inter 2000 rise 2 fall 5
  server k8s-worker01 192.168.10.21:32222  check inter 2000 rise 2 fall 5
  server k8s-worker02 192.168.10.22:32222  check inter 2000 rise 2 fall 5
  server k8s-worker03 192.168.10.23:32222  check inter 2000 rise 2 fall 5
listen mgmt-prometheus
  bind *:32221
  mode http
  server k8s-master01 192.168.10.11:32221  check inter 2000 rise 2 fall 5
  server k8s-master02 192.168.10.12:32221  check inter 2000 rise 2 fall 5
  server k8s-master03 192.168.10.13:32221  check inter 2000 rise 2 fall 5
  server k8s-worker01 192.168.10.21:32221  check inter 2000 rise 2 fall 5
  server k8s-worker02 192.168.10.22:32221  check inter 2000 rise 2 fall 5
  server k8s-worker03 192.168.10.23:32221  check inter 2000 rise 2 fall 5
```

---

# **3. Thanos Install**

## **3-1. Values.yaml 수정**

- persistence: storageClass: “수정”
- node label 지정 : `kubectl label nodes [NodeName] node=infra`

```
compactor:
  nodeSelector:
    node: infra
query:
   nodeSelector:
    node: infra
bucketweb:
   nodeSelector:
    node: infra
storegateway:
  nodeSelector:
    node: infra
ruler:
  nodeSelector:
    node: infra
  persistence:
    enabled: true
    type: sts
    storageClassName: "수정"
    accessModes:
      - ReadWriteOnce
    size: 20Gi
    finalizers:
      - kubernetes.io/pvc-protection
```

## **3-2. Thanos helm install**

```
:~/backup/platform-monitoring/1.mgmt/3.thanos# helm install thanos . -n monitoring
```

- 배포 확인

```
kubectl get pods -n monitoring | grep thanos
thanos-bucketweb-7885f6bb96-k2qqr                        1/1     Running   0             2d5h
thanos-compactor-9f6454f85-ld92z                         1/1     Running   0             2d5h
thanos-query-64b87c874d-l78lw                            1/1     Running   0             2d5h
thanos-query-64b87c874d-t49bc                            1/1     Running   0             2d5h
thanos-query-frontend-79bf557659-72rfq                   1/1     Running   0             2d5h
thanos-ruler-0                                           1/1     Running   0             2d5h
thanos-storegateway-0                                    1/1     Running   0             2d5h
thanos-storegateway-1                                    1/1     Running   0             2d5h
```

- secret 확인

```
thanos-objstore-secret                 Opaque               1      2d5h
```

## **3-3. MGMT HAProxy 설정 ( Thanos )**

- `Thanos-query-frontend` : `32223`

```
listen mgmt-thanos-query-frontend
  bind *:32223
  mode http
  server k8s-master01 192.168.10.11:32223  check inter 2000 rise 2 fall 5
  server k8s-master02 192.168.10.12:32223  check inter 2000 rise 2 fall 5
  server k8s-master03 192.168.10.13:32223  check inter 2000 rise 2 fall 5
  server k8s-worker01 192.168.10.21:32223  check inter 2000 rise 2 fall 5
  server k8s-worker02 192.168.10.22:32223  check inter 2000 rise 2 fall 5
  server k8s-worker03 192.168.10.23:32223  check inter 2000 rise 2 fall 5
```

---

## **3-4. Thanos 접속 확인**

- [Thanos Console](http://203.0.113.10:32223/stores)
    - Sidecar 부분의 EndPoint 는 biz 클러스터의 프로메테우스 배포시 추가됩니다.
    - Status > Target 부분 확인
