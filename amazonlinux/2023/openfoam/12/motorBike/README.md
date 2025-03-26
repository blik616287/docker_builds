# aws - eks & fsx - armada_client - cfd motorBike foamRun

hello moto

## obligatory click me
 
[![they_call_him___doom_slayer](https://img.youtube.com/vi/UbkDJXKm3sY/maxresdefault.jpg)](https://www.youtube.com/watch?v=UbkDJXKm3sY)

## required plumbing
- eks
  - coredns
  - fsx plugin
- fsx sc & pvc
- armada operator
- armada_client
- compatible container images
  - openfoam12 + thirdparty support
  - analysis layers

### submit job - from working dir
```bash
kubectl port-forward -n armada service/armada-lookout 8080:8080
kubectl port-forward -n armada service/armada-server 50051:50051
pip install armada_client
./rip_and_tear.sh
```
