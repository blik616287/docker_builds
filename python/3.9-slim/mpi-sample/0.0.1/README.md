# mpi implementation - development

currently spawns 3 pods, master and 2x workers

mpi implementation is not working because of networking, but i have a fix for this using coredns

each container mounts a shared readwritemany block to /app/shared

currently fails on master, and sleeps infinity on workers for testing purposes 

## pvc dependancy
```yaml
root@kube-controller1:~# cat mpi-shared-data-pvc.yaml 
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  annotations:
    volume.beta.kubernetes.io/storage-provisioner: rook-ceph.rbd.csi.ceph.com
    volume.kubernetes.io/storage-provisioner: rook-ceph.rbd.csi.ceph.com
  creationTimestamp: "2025-03-13T21:04:00Z"
  finalizers:
  - kubernetes.io/pvc-protection
  name: mpi-shared-data
  namespace: default
  resourceVersion: "46267"
  uid: c2d5e348-abc8-4dba-99af-5e6de0e8c6aa
spec:
  accessModes:
  - ReadWriteMany
  resources:
    requests:
      storage: 10Gi
  storageClassName: rook-ceph-block
  volumeMode: Block
status:
  phase: Pending
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
