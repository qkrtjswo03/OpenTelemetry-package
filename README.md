# 1. Git Clone

1. 먼저, Backup 디렉토리를 생성 합니다.

```bash
mkdir backup ; cd backup
```

1. git clone 으로 해당 패키징 파일을 다운로드 합니다.

```bash
git clone https://101.202.40.5:30000/Viola/viola-monitoring.git
Cloning into 'viola-monitoring'...
Username for 'https://101.202.40.5:30000': sjpark
Password for 'https://sjpark@101.202.40.5:30000':
remote: Enumerating objects: 2076, done.
remote: Counting objects: 100% (2076/2076), done.
remote: Compressing objects: 100% (1138/1138), done.
remote: Total 2076 (delta 1058), reused 1866 (delta 900), pack-reused 0
Receiving objects: 100% (2076/2076), 67.41 MiB | 30.21 MiB/s, done.
Resolving deltas: 100% (1058/1058), done.
```

1. 패키징 디렉토리(viola-monitoring)를 확인합니다.

```bash
~/backup/viola-monitoring# ll
drwxr-xr-x 5 root root  4096 May 21 14:27 1.mgmt/
drwxr-xr-x 8 root root  4096 May 21 14:29 2.biz/
-rw-r--r-- 1 root root 66435 May 19 13:37 README.md
```

1.  번호 순서대로 작업을 진행하면 됩니다.
- `1. mgmt : MGMT Cluster 에서 배포 될 컨포넌트 (grafana,prometheus,thanos,minio)`
- `2. biz : biz Cluster 에서 배포 될 컨포넌트(grafana,prometheus,minio, Opentelemetry,Loki,Tempo,Promail)`
