# aws - eks & fsx - pingpong mpi test

launches pingpong mpi test case with armada_client on EKS
fsx drive for shared storage and job state tracking
includes heartbeats for monitoring successful job completion and exit

## obligatory
 
[![ClickMe](https://img.youtube.com/vi/ESQhptIhD8A/maxresdefault.jpg)](https://www.youtube.com/watch?v=ESQhptIhD8A)

## required plumbing
- eks
  - coredns
  - fsx plugin
- fsx sc & pvc
- armada operator
- armada_client
- compatible container image

## quick start
```bash
make publish OS=amazonlinux OS_VERSION=2023 PKG=pingpong PKG_VERSION=0.0.1
kubectl port-forward -n armada service/armada-lookout 8080:8080
kubectl port-forward -n armada service/armada-server 50051:50051
./config_mpi.py
```

## armada_client scheduling pods
```bash
(base) > $ ./config_mpi.py
2025-03-20 16:24:26,717 - __main__ - INFO - Creating/verifying queue: mpi-queue-bea65da9
2025-03-20 16:24:26,997 - __main__ - INFO - Queue mpi-queue-bea65da9 not found, creating new queue
2025-03-20 16:24:27,063 - __main__ - INFO - Queue mpi-queue-bea65da9 created successfully
2025-03-20 16:24:27,063 - __main__ - INFO - Verifying queue mpi-queue-bea65da9 exists (attempt 1/5)
2025-03-20 16:24:27,132 - __main__ - INFO - Queue mpi-queue-bea65da9 verified to exist
2025-03-20 16:24:27,132 - __main__ - INFO - Using queue: mpi-queue-bea65da9
2025-03-20 16:24:27,132 - __main__ - INFO - Waiting 10s for queue to be fully ready
2025-03-20 16:24:37,217 - __main__ - INFO - Queue mpi-queue-bea65da9 is ready for job submission
2025-03-20 16:24:37,217 - __main__ - INFO - IMPORTANT: A PVC named fsx-claim must exist in namespace default
2025-03-20 16:24:37,217 - __main__ - INFO - The PVC should have accessModes: ReadWriteMany
2025-03-20 16:24:37,217 - __main__ - INFO - Using FSX for shared filesystem access
2025-03-20 16:24:37,217 - __main__ - INFO - Creating MPI job set mpi-jobset-e2f40d95 with 2 processes
2025-03-20 16:24:37,217 - __main__ - INFO - Created PVC source with claimName=fsx-claim, readOnly=False
2025-03-20 16:24:37,217 - __main__ - INFO - Created Volume 'persistent-storage' with PVC claim 'fsx-claim'
2025-03-20 16:24:37,217 - __main__ - INFO - Created volume 'persistent-storage' referencing PVC 'fsx-claim'
2025-03-20 16:24:37,218 - __main__ - INFO - Created PVC source with claimName=fsx-claim, readOnly=False
2025-03-20 16:24:37,218 - __main__ - INFO - Created Volume 'persistent-storage' with PVC claim 'fsx-claim'
2025-03-20 16:24:37,218 - __main__ - INFO - Created volume 'persistent-storage' referencing PVC 'fsx-claim'
2025-03-20 16:24:37,218 - __main__ - INFO - Submitting job set to queue mpi-queue-bea65da9
2025-03-20 16:24:37,301 - __main__ - INFO - Submitted job set mpi-jobset-e2f40d95
2025-03-20 16:24:37,301 - __main__ - INFO - Master job ID: 01jptq37r6wmm8bm5s35cdja0e
2025-03-20 16:24:37,301 - __main__ - INFO - Worker job IDs: ['01jptq37r6wmm8bm5s36sxa96s']
2025-03-20 16:24:37,301 - __main__ - INFO - Important: All pods use FSX PVC 'fsx-claim' mounted at /app/shared
2025-03-20 16:24:37,301 - __main__ - INFO - Make sure PVC 'fsx-claim' exists in namespace default
2025-03-20 16:24:37,301 - __main__ - INFO - The PVC should be used with ReadWriteMany access mode with proper RBAC permissions
2025-03-20 16:24:37,301 - __main__ - INFO - All pods will run with minimal resource constraints (100m CPU, 100Mi memory)
2025-03-20 16:24:37,301 - __main__ - INFO - MPI job set mpi-jobset-e2f40d95 submitted successfully
2025-03-20 16:24:37,301 - __main__ - INFO - Using FSX PVC fsx-claim mounted at /app/shared
2025-03-20 16:24:37,301 - __main__ - INFO - All pods will run with minimal resource constraints (100m CPU, 100Mi memory)
2025-03-20 16:24:37,301 - __main__ - INFO - Monitoring job set mpi-jobset-e2f40d95 with 300s timeout
2025-03-20 16:24:39,379 - __main__ - INFO - Job 01jptq37r6wmm8bm5s35cdja0e - EventType.submitted
2025-03-20 16:24:39,379 - __main__ - INFO - Job 01jptq37r6wmm8bm5s35cdja0e - EventType.queued
2025-03-20 16:24:39,379 - __main__ - INFO - Job 01jptq37r6wmm8bm5s36sxa96s - EventType.submitted
2025-03-20 16:24:39,379 - __main__ - INFO - Job 01jptq37r6wmm8bm5s36sxa96s - EventType.queued
2025-03-20 16:24:42,370 - __main__ - INFO - Job 01jptq37r6wmm8bm5s35cdja0e - EventType.leased
2025-03-20 16:24:42,370 - __main__ - INFO - Job 01jptq37r6wmm8bm5s36sxa96s - EventType.leased
2025-03-20 16:24:50,629 - __main__ - INFO - Job 01jptq37r6wmm8bm5s36sxa96s - EventType.pending
2025-03-20 16:24:50,629 - __main__ - INFO - Job 01jptq37r6wmm8bm5s35cdja0e - EventType.pending
2025-03-20 16:24:54,658 - __main__ - INFO - Job 01jptq37r6wmm8bm5s35cdja0e - EventType.running
2025-03-20 16:24:54,659 - __main__ - INFO - Job 01jptq37r6wmm8bm5s36sxa96s - EventType.running
2025-03-20 16:25:27,395 - __main__ - INFO - Job 01jptq37r6wmm8bm5s35cdja0e - EventType.succeeded
2025-03-20 16:25:27,396 - __main__ - INFO - Job 01jptq37r6wmm8bm5s36sxa96s - EventType.succeeded
2025-03-20 16:25:27,396 - __main__ - INFO - All jobs in job set mpi-jobset-e2f40d95 completed successfully
2025-03-20 16:25:27,396 - __main__ - INFO - MPI job completed successfully
```

## mpi results
```bash
(base) > $ kubectl -n default logs armada-01jptq37r6wmm8bm5s35cdja0e-0
Container starting up
Hostname: armada-01jptq37r6wmm8bm5s35cdja0e-0
MPI_RANK: 0
MPI_WORLD_SIZE: 2
JOB_SET_ID: mpi-jobset-e2f40d95
POD_NAME: mpi-0-mpi-jobset-e2f40d95
ssh-keygen: generating new host keys: RSA DSA ECDSA ED25519 
Master node (Rank 0) setting up SSH keys
Generating public/private rsa key pair.
Your identification has been saved in /root/.ssh/id_rsa
Your public key has been saved in /root/.ssh/id_rsa.pub
The key fingerprint is:
SHA256:sy117uvY34cNZod6kH2JTuEkHPUJHWiWAXXGEEAPPf8 root@armada-01jptq37r6wmm8bm5s35cdja0e-0
The key's randomart image is:
+---[RSA 3072]----+
|          .=*BO+.|
|           .oB=o.|
|          . +.oo |
|           o o . |
|        S . =oo.o|
|         = oo+*.E|
|        o . += * |
|         . +..o.o|
|          ..=+. o|
+----[SHA256]-----+
Found 1 host files, waiting for 2...
Found 2 host files, proceeding...
Added host to hostfile: 10-0-141-33.default.pod.cluster.local
Added host to hostfile: 10-0-140-221.default.pod.cluster.local
Testing SSH connections to all nodes
Testing SSH to 10-0-141-33.default.pod.cluster.local
Starting master heartbeat mechanism
SSH connection to 10-0-141-33.default.pod.cluster.local successful
Testing SSH to 10-0-140-221.default.pod.cluster.local
SSH connection to 10-0-140-221.default.pod.cluster.local successful
Master node starting MPI application
 Data for JOB [41773,1] offset 0 Total slots allocated 2

 ========================   JOB MAP   ========================

 Data for node: armada-01jptq37r6wmm8bm5s35cdja0e-0	Num slots: 1	Max slots: 1	Num procs: 1
 	Process OMPI jobid: [41773,1] App: 0 Process rank: 0 Bound: socket 0[core 0[hwt 0-1]]:[BB/../../../../../../../../../../../../../../../../../../../../../../..]

 Data for node: 10-0-140-221.default.pod.cluster.local	Num slots: 1	Max slots: 1	Num procs: 1
 	Process OMPI jobid: [41773,1] App: 0 Process rank: 1 Bound: N/A

 =============================================================
Process 0 on armada-01jptq37r6wmm8bm5s35cdja0e-0
Process 1 on armada-01jptq37r6wmm8bm5s36sxa96s-0
Starting ping-pong test (iterations: 10, message size: 1000000 bytes)
Process 0 sent and received ping-pong 0 in 0.091995 seconds
Process 1 sent and received ping-pong 1 in 0.001164 seconds
Process 0 sent and received ping-pong 2 in 0.000911 seconds
Process 1 sent and received ping-pong 3 in 0.000815 seconds
Process 0 sent and received ping-pong 4 in 0.000803 seconds
Process 1 sent and received ping-pong 5 in 0.000805 seconds
Process 0 sent and received ping-pong 6 in 0.000789 seconds
Process 1 sent and received ping-pong 7 in 0.000793 seconds
Process 0 sent and received ping-pong 8 in 0.000796 seconds

=== Ping-pong Test Results ===
Total time: 0.095294 seconds
Average time per round-trip: 0.009529 seconds
Bandwidth: 200.153643 MB/s
Process 1 sent and received ping-pong 9 in 0.000794 seconds
MPI application completed with exit status: 0
Master cleanup done with status 0
```
