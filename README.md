# PerSSD-NVMe: Kubernetes operator for Persistent, Shared, and Scalable Data when deploying local NVMe SSDs for scientific workflows
<a href="https://www.python.org/downloads/release/python-310/"><img alt="Python 3.10" src="https://img.shields.io/badge/Python-3.10-3776AB.svg?style=flat&logo=python&logoColor=white"></a>
<a href="https://www.docker.com"><img alt="Docker" src="https://badges.aleen42.com/src/docker.svg"></a>
<a href="https://kubernetes.io/"><img alt="Kubernetes" src="https://img.shields.io/badge/kubernetes-%23326ce5.svg?style=for-the-badge&logo=kubernetes&logoColor=white" width="85" height="20"></a>
<a href="https://opensource.org/licenses/Apache-2.0"><img alt="License" src="https://img.shields.io/badge/License-Apache_2.0-green.svg"></a>

## Overview - About
PerSSD-NVMe is a Kubernetes/OpenShift operator that plays as the "burst buffer" layer to track and save data on persistent storage (i.e., object storage) when the application leverages the high throughput and low latency of reading and writing data from and to local NVMe SSDs. 

Traditional HPC, AI, and data-driven workflows often have persistent data objects both from intermediate states as well as final outputs. Moving these workflows to the cloud causes a dramatic I/O performance impact because of the remote, relatively slow storage. Using node-local storage, properly managed, these data objects can be preserved more efficiently than writing directly to remote object storage.

## Prerequisites
The user must have access to a Kubernetes/OpenShift cluster where they have the [Kubeflow](https://www.kubeflow.org/) or [open-data-hub](https://opendatahub.io/) operator. 
On your local computer, you only need the python kubeflow to compile your pipeline and kopf to compile your operator. 
* `pip install kfp==1.8`
* `pip install kopf`
  
## Running
The user would need to be logged into their cloud vendor of preference and have access to the cluster. 
Once they have access, they need to:  
1. Activate your operator: `kopf run pers-nvme-operator.py --verbose` on your terminal
2. Compile your python kubeflow pipeline code: `python3 pipeline.py` - This will generate `yaml` files that can be executed now in Kubernete, for example `pipeline.yaml`. 
3. Create the workflow in Kubernetes: `kubectl create pipeline.yaml`
4. Track and monitor the execution: `kubectl get pods` 


## Related Publications
* P. Olaya et al., "Building Trust in Earth Science Findings through Data Traceability and Results Explainability," in IEEE Transactions on Parallel and Distributed Systems, vol. 34, no. 2, pp. 704-717, 1 Feb. 2023, doi: [10.1109/TPDS.2022.3220539](https://ieeexplore.ieee.org/abstract/document/9942337).
* P. Olaya et al., "Enabling Scalability in the Cloud for Scientific Workflows: An Earth Science Use Case," 2023 IEEE 16th International Conference on Cloud Computing (CLOUD), Chicago, IL, USA, 2023, pp. 383-393, doi: [10.1109/CLOUD60044.2023.00052](https://ieeexplore.ieee.org/document/10255013). 

## Acknowledgments
The authors acknowledge the support of IBM through a Shared University Research Award; Sandia National Laboratories; the National Science Foundation through the grant numbers #2028923, #2103845, #2103836, and #2138811; and the Access program through the NSF grant #2138296.
Any opinions, findings, conclusions, or recommendations expressed in this material are those of the author(s) and do not necessarily reflect the views of the National Science Foundation. 

## Contact Info
Paula Olaya: polaya@vols.utk.edu  
Michela Taufer: mtaufer@utk.edu

## Copyright and License 
Copyright (c) 2023, Global Computing Lab

PerSSD-NVMe is distributed under terms of the [Apache License, Version 2.0](http://www.apache.org/licenses/LICENSE-2.0) with LLVM Exceptions.
See [LICENSE](https://github.com/TauferLab/pers-nvme/blob/main/LICENSE) for more details.
