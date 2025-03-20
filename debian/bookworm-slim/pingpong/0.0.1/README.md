# pingpong mpi test

Due to the pvc dependancies, this only currently works with blik616287/k8s_antzy_vagrant

## pvc dependancy
```yaml
cat > cephfs.yaml <<EOF 
apiVersion: ceph.rook.io/v1
kind: CephFilesystem
metadata:
  name: myfs
  namespace: rook-ceph
spec:
  metadataPool:
    replicated:
      size: 3
  dataPools:
    - name: data0
      replicated:
        size: 3
  metadataServer:
    activeCount: 1
    activeStandby: true
EOF

cat > cephfs-storageclass.yaml << EOF
root@kube-controller1:~/armada-operator# cat cephfs-storageclass.yaml 
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: rook-cephfs
provisioner: rook-ceph.cephfs.csi.ceph.com
parameters:
  clusterID: rook-ceph
  fsName: myfs
  pool: myfs-data0
  csi.storage.k8s.io/provisioner-secret-name: rook-csi-cephfs-provisioner
  csi.storage.k8s.io/provisioner-secret-namespace: rook-ceph
  csi.storage.k8s.io/controller-expand-secret-name: rook-csi-cephfs-provisioner
  csi.storage.k8s.io/controller-expand-secret-namespace: rook-ceph
  csi.storage.k8s.io/node-stage-secret-name: rook-csi-cephfs-node
  csi.storage.k8s.io/node-stage-secret-namespace: rook-ceph
reclaimPolicy: Delete
volumeBindingMode: Immediate
allowVolumeExpansion: true
EOF

cat > mpi-shared-pvc.yaml <<EOF 
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: mpi-shared-data-cephfs
  namespace: default
spec:
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 10Gi
  storageClassName: rook-cephfs
EOF

kubectl apply -f cephfs.yaml
kubectl apply -f cephfs-storageclass.yaml
kubectl apply -f mpi-shared-pvc.yaml
```

## config mpi run
```python
>>> main()
2025-03-19 18:46:01,354 - __main__ - INFO - Creating/verifying queue: mpi-queue-330b825b
2025-03-19 18:46:01,357 - __main__ - INFO - Queue mpi-queue-330b825b not found, creating new queue
2025-03-19 18:46:01,363 - __main__ - INFO - Queue mpi-queue-330b825b created successfully
2025-03-19 18:46:01,363 - __main__ - INFO - Verifying queue mpi-queue-330b825b exists (attempt 1/5)
2025-03-19 18:46:01,365 - __main__ - INFO - Queue mpi-queue-330b825b verified to exist
2025-03-19 18:46:01,365 - __main__ - INFO - Using queue: mpi-queue-330b825b
2025-03-19 18:46:01,365 - __main__ - INFO - Waiting 10s for queue to be fully ready
2025-03-19 18:46:11,377 - __main__ - INFO - Queue mpi-queue-330b825b is ready for job submission
2025-03-19 18:46:11,377 - __main__ - INFO - IMPORTANT: A PVC named mpi-shared-data-cephfs must exist in namespace default
2025-03-19 18:46:11,377 - __main__ - INFO - The PVC should have volumeMode: Filesystem, accessModes: ReadWriteMany
2025-03-19 18:46:11,377 - __main__ - INFO - And use storage class rook-cephfs
2025-03-19 18:46:11,377 - __main__ - INFO - Using CephFS for true ReadWriteMany shared filesystem access
2025-03-19 18:46:11,377 - __main__ - INFO - Creating MPI job set mpi-jobset-18ec9d7a with 2 processes
2025-03-19 18:46:11,378 - __main__ - INFO - Volume fields: ['name', 'volumeSource']
2025-03-19 18:46:11,378 - __main__ - INFO - VolumeSource fields: ['hostPath', 'emptyDir', 'gcePersistentDisk', 'awsElasticBlockStore', 'gitRepo', 'secret', 'nfs', 'iscsi', 'glusterfs', 'persistentVolumeClaim', 'rbd', 'flexVolume', 'cinder', 'cephfs', 'flocker', 'downwardAPI', 'fc', 'azureFile', 'configMap', 'vsphereVolume', 'quobyte', 'azureDisk', 'photonPersistentDisk', 'projected', 'portworxVolume', 'scaleIO', 'storageos', 'csi', 'ephemeral']
2025-03-19 18:46:11,378 - __main__ - INFO - Found field structure: Volume.volumeSource.persistentVolumeClaim
2025-03-19 18:46:11,378 - __main__ - INFO - PVC source fields: ['claimName', 'readOnly']
2025-03-19 18:46:11,378 - __main__ - INFO - Created PVC source with claimName=mpi-shared-data-cephfs, readOnly=False
2025-03-19 18:46:11,378 - __main__ - INFO - Created VolumeSource with persistentVolumeClaim field
2025-03-19 18:46:11,378 - __main__ - INFO - Created Volume with volumeSource field
2025-03-19 18:46:11,378 - __main__ - INFO - Created volume referencing PVC mpi-shared-data-cephfs
2025-03-19 18:46:11,378 - __main__ - INFO - Volume fields: ['name', 'volumeSource']
2025-03-19 18:46:11,378 - __main__ - INFO - VolumeSource fields: ['hostPath', 'emptyDir', 'gcePersistentDisk', 'awsElasticBlockStore', 'gitRepo', 'secret', 'nfs', 'iscsi', 'glusterfs', 'persistentVolumeClaim', 'rbd', 'flexVolume', 'cinder', 'cephfs', 'flocker', 'downwardAPI', 'fc', 'azureFile', 'configMap', 'vsphereVolume', 'quobyte', 'azureDisk', 'photonPersistentDisk', 'projected', 'portworxVolume', 'scaleIO', 'storageos', 'csi', 'ephemeral']
2025-03-19 18:46:11,378 - __main__ - INFO - Found field structure: Volume.volumeSource.persistentVolumeClaim
2025-03-19 18:46:11,378 - __main__ - INFO - PVC source fields: ['claimName', 'readOnly']
2025-03-19 18:46:11,378 - __main__ - INFO - Created PVC source with claimName=mpi-shared-data-cephfs, readOnly=False
2025-03-19 18:46:11,378 - __main__ - INFO - Created VolumeSource with persistentVolumeClaim field
2025-03-19 18:46:11,378 - __main__ - INFO - Created Volume with volumeSource field
2025-03-19 18:46:11,378 - __main__ - INFO - Created volume referencing PVC mpi-shared-data-cephfs
2025-03-19 18:46:11,378 - __main__ - INFO - Submitting job set to queue mpi-queue-330b825b
2025-03-19 18:46:11,406 - __main__ - INFO - Submitted job set mpi-jobset-18ec9d7a
2025-03-19 18:46:11,406 - __main__ - INFO - Master job ID: 01jprcxrtm1d2qnw72x23m4tnx
2025-03-19 18:46:11,406 - __main__ - INFO - Worker job IDs: ['01jprcxrtm1d2qnw72x3s1empm']
2025-03-19 18:46:11,406 - __main__ - INFO - Important: All pods use CephFS PVC mpi-shared-data-cephfs mounted at /app/shared
2025-03-19 18:46:11,406 - __main__ - INFO - Make sure PVC mpi-shared-data-cephfs exists in namespace default with volumeMode: Filesystem
2025-03-19 18:46:11,406 - __main__ - INFO - The PVC should be used with ReadWriteMany access mode with proper RBAC permissions
2025-03-19 18:46:11,406 - __main__ - INFO - MPI job set mpi-jobset-18ec9d7a submitted successfully
2025-03-19 18:46:11,406 - __main__ - INFO - Using CephFS PVC mpi-shared-data-cephfs mounted at /app/shared
2025-03-19 18:46:11,406 - __main__ - INFO - Monitoring job set mpi-jobset-18ec9d7a with 300s timeout
2025-03-19 18:46:13,464 - __main__ - INFO - Job 01jprcxrtm1d2qnw72x23m4tnx - EventType.submitted
2025-03-19 18:46:13,465 - __main__ - INFO - Job 01jprcxrtm1d2qnw72x23m4tnx - EventType.queued
2025-03-19 18:46:13,465 - __main__ - INFO - Job 01jprcxrtm1d2qnw72x3s1empm - EventType.submitted
2025-03-19 18:46:13,465 - __main__ - INFO - Job 01jprcxrtm1d2qnw72x3s1empm - EventType.queued
2025-03-19 18:46:13,465 - __main__ - INFO - Job 01jprcxrtm1d2qnw72x23m4tnx - EventType.leased
2025-03-19 18:46:13,465 - __main__ - INFO - Job 01jprcxrtm1d2qnw72x3s1empm - EventType.leased
2025-03-19 18:46:19,974 - __main__ - INFO - Job 01jprcxrtm1d2qnw72x23m4tnx - EventType.pending
2025-03-19 18:46:19,974 - __main__ - INFO - Job 01jprcxrtm1d2qnw72x3s1empm - EventType.pending
2025-03-19 18:46:39,650 - __main__ - INFO - Job 01jprcxrtm1d2qnw72x3s1empm - EventType.running
2025-03-19 18:46:43,528 - __main__ - INFO - Job 01jprcxrtm1d2qnw72x23m4tnx - EventType.running
```

## mpi results
```bash
root@kube-controller1:~/armada-operator# kubectl -n default logs armada-01jprcxrtm1d2qnw72x23m4tnx-0Container starting up
Hostname: armada-01jprcxrtm1d2qnw72x23m4tnx-0
MPI_RANK: 0
MPI_WORLD_SIZE: 2
JOB_SET_ID: mpi-jobset-18ec9d7a
POD_NAME: mpi-0-mpi-jobset-18ec9d7a
Starting OpenBSD Secure Shell server: sshd.
Master node (Rank 0) setting up SSH keys
Generating public/private rsa key pair.
Your identification has been saved in /root/.ssh/id_rsa
Your public key has been saved in /root/.ssh/id_rsa.pub
The key fingerprint is:
SHA256:gboAYKypHWVzcKuc2Ec5Qh80YTcLmuz69TQ0ut7rBjo root@armada-01jprcxrtm1d2qnw72x23m4tnx-0
The key's randomart image is:
+---[RSA 3072]----+
|o.  ooO.o        |
|o. o+*.O o       |
|o. o=oB o        |
|o..= * . .       |
|..o.B . S        |
|. .o o.o .       |
|  . ..o.o        |
|   .E. =..       |
|    .ooo=.       |
+----[SHA256]-----+
Found 1 host files, waiting for 2...
Found 2 host files, proceeding...
Testing SSH connections to all nodes
Testing SSH to 10-224-13-38.default.pod.cluster.local
SSH connection to 10-224-13-38.default.pod.cluster.local successful
Master node starting MPI application
Process 1 on armada-01jprcxrtm1d2qnw72x23m4tnx-0
Process 0 on armada-01jprcxrtm1d2qnw72x23m4tnx-0
Starting ping-pong test (iterations: 10, message size: 1000000 bytes)
Process 0 sent and received ping-pong 0 in 0.000993 seconds
Process 1 sent and received ping-pong 1 in 0.000668 seconds
Process 0 sent and received ping-pong 2 in 0.000431 seconds
Process 1 sent and received ping-pong 3 in 0.010292 seconds
Process 0 sent and received ping-pong 4 in 0.000481 seconds
Process 1 sent and received ping-pong 5 in 0.000490 seconds
Process 0 sent and received ping-pong 6 in 0.000400 seconds
Process 1 sent and received ping-pong 7 in 0.000422 seconds
Process 0 sent and received ping-pong 8 in 0.000362 seconds
Process 1 sent and received ping-pong 9 in 0.000405 seconds

=== Ping-pong Test Results ===
Total time: 0.002667 seconds
Average time per round-trip: 0.000267 seconds
Bandwidth: 7152.650358 MB/s
```

## todo
- fix clean exit on master/workers
- aws fsx pvc
