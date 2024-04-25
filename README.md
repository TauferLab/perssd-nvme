# PerSSD-NVMe: Kubernetes Operator for Persistent, Shared, and Scalable Data when deploying local NVMe SSDs for scientific workflows
## Overview - About
PerSSD-NVMe is a Kubernetes/OpenShift operator that plays as the "burst buffer" layer to track and save data on persistent storage (i.e., object storage) when the application leverages the high throughput and low latency of reading and writing data from and to local NVMe SSDs. 

Traditional HPC, AI, and data-driven workflows often have persistent data objects both from intermediate states as well as final outputs. Moving these workflows to the cloud causes a dramatic I/O performance impact because of the remote, relatively slow storage. Using node-local storage, properly managed, these data objects can be preserved more efficiently than writing directly to remote object storage.

## Prerequisites - dependencies
List all dependencies or software packages required to install or run your project fully

## Installation
List all the steps needed to install (compile) your project.

## Using - Running
List all the steps to run your project as well as the different arguments or options you have to execute it.

## Related Publications
List the publications related to this project

## Copyright and License (Optional but required to add LICENSE file)
Add the license. In case this new repo belongs to another project, copy the used license of the other project. if not, you can use this as a template but discuss it with Dr T.
```
## Copyright and License

Copyright (c) 2023, Global Computing Lab

PerSSD-NVMe is distributed under terms of the [Apache License, Version 2.0](http://www.apache.org/licenses/LICENSE-2.0) with LLVM Exceptions.
See [LICENSE](https://github.com/TauferLab/) for more details.

```

## Acknowledgments
Use the next template using the correct name of the project and the grant numbers:
```
<NAME_OF_PROJECT> is funded by the National Science Foundation (NSF) under grant numbers ### and ###. 
Any opinions, findings, and conclusions, or recommendations expressed in this material are those of the author(s) and do not necessarily reflect the views of the National Science Foundation. 
```

## Contact Info (optional)
Add your and Dr. T's email
