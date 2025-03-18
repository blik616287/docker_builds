# mpi implementation - development

currently spawns 3 pods, master and 2x workers

mpi implementation is not working because of networking, but i have a fix for this using coredns

each container mounts a shared readwritemany block to /app/shared

currently fails on master, and sleeps infinity on workers for testing purposes 

## pvc dependancy
```yaml
root@kube-controller1:~# cat cephfs.yaml 
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
  # These secrets are created automatically by the Rook operator
  csi.storage.k8s.io/provisioner-secret-name: rook-csi-cephfs-provisioner
  csi.storage.k8s.io/provisioner-secret-namespace: rook-ceph
  csi.storage.k8s.io/controller-expand-secret-name: rook-csi-cephfs-provisioner
  csi.storage.k8s.io/controller-expand-secret-namespace: rook-ceph
  csi.storage.k8s.io/node-stage-secret-name: rook-csi-cephfs-node
  csi.storage.k8s.io/node-stage-secret-namespace: rook-ceph
reclaimPolicy: Delete
volumeBindingMode: Immediate
allowVolumeExpansion: true

root@kube-controller1:~/armada-operator# cat mpi-shared-pvc.yaml 
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
```

## todo
- lots of cargo code, need a full refactor on full working mpi example
  - that or we take the working example, port to aws, and do the cleanup there
  - i mean whats the point in refactoring code that only works on my virtualboxes
- implement lookup fix for networking communication between pods 
- pod name not being set appropriately
- continue testing mpi workflow folling network fix
- migration to aws will likely change alot about the storage setup 
- it makes sense to abstract out the pvc creation from the submission script, perhaps we have an intermediate service which performs that action plus the submission to armada
  - but im not convinced as i think the general use case will be people run multiple jobs on a large network mounted scratch space, so it might not be worth it, before testing implementation on aws storage
