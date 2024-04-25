import kopf
import logging
from kubernetes import client, config, watch
from python_settings import settings
import json
import sqlite3
from sqlite3 import Error

# Database Functions
def create_connection(path):
    connection = None
    try:
        connection = sqlite3.connect(path, check_same_thread=False)
    except Error as e:
        logging.info(f"The error '{e}' occurred")
    return connection

def execute_query(connection, query):
    cursor = connection.cursor()
    try:
        cursor.execute(query)
        connection.commit()
    except Error as e:
        logging.info(f"The error '{e}' occurred")


@kopf.on.startup()
def configure(settings: kopf.OperatorSettings, **_):
    settings.posting.level = logging.WARNING
    settings.watching.connect_timeout = 1 * 60
    settings.watching.server_timeout = 10 * 60
    global connection
    connection = create_connection("test.sqlite")
    connection.execute("DROP TABLE IF EXISTS pods")
    table = """
    CREATE TABLE pods (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      podname TEXT NOT NULL,
      node TEXT,
      outputs TEXT,
      pushed TEXT
    );
    """
    execute_query(connection, table)  

#@kopf.on.update('pipelinerun')
#def track_pipelineruns(body, **kwargs):
#    logging.info(f"Pipeline {body['status']['conditions'][0]['reason']} and {body['status']['conditions'][0]['status']}")
#    while not body['status']['conditions'][0]['reason'] == 'Succeeded':
#        #logging.info(f"Pipeline running")
#    else:
#        logging.info(f"Pipeline stopped")



@kopf.on.update('Pod',
        labels={'app.kubernetes.io/managed-by': 'tekton-pipelines'})
def track_tasks(body, **kwargs):
    
    # Start k8s client
    #v1 = client.CoreV1Api()

    #logging.info(f"{body}")
    # Watching the statuses of all pods
    namespace = body['metadata']['namespace']
    logging.info(f"POD {body['metadata']['name']}")
    logging.info(f"STATUS {body['status']['containerStatuses'][0]['state'].keys()}")

    # Check if the pod completes
    if list(body['status']['containerStatuses'][0]['state'].keys())[0]=='terminated': 
        message=body['status']['containerStatuses'][0]['state']['terminated']['message']
        outputs=list(eval(message))
        # Check if the pod has an output (task pod) or if it has a manifest (pvc creation pod)
        outs_list=[]
        if outputs[0]['key'] != 'manifest':
            # If it's a task pod we aim to gather the name of the pod, the node, and the output data generated
            # Get the outputs
            [outs_list.append(x['value']) for x in outputs[:-1]]
            outs_str = " ".join(outs_list)
            # Information about the pod
            # Podname and outputs
            logging.info(f"The name of the pod is {body['metadata']['name']} and its output is {outs_list}")
            # Extract annotations and turn them from str to dict
            annotations = json.loads(body['metadata']['annotations']['kopf.zalando.org/last-handled-configuration'])
            # Volumes related to the application --OO hardcoded to nvme and cos in this case
            #logging.info(f"{len(annotations['spec']['volumes'])} volumes in the pod {annotations['spec']['volumes'][9:11]}")
            # Get the nodename
            node = annotations['spec']['nodeName']

            # Insert entry in database
            connection.execute("INSERT INTO pods (podname, node, outputs, pushed) VALUES(?, ?, ?, ?)",
                                                  (body['metadata']['name'], node, outs_str, "False"))
            connection.commit()

            # Query the database 

     

            # Volume definition
            # If I want to create the PVC, check: v1.create_namespaced_persistent_volume_claim(<namespace>, <body>) 
            #volume_nvme = client.V1Volume(name='nvme',host_path=client.V1HostPathVolumeSource(path='/var/data'))
            #volumem_nvme = client.V1VolumeMount(
            #                name="nvme",
            #                mount_path="/nvme",
            #            )
            pvc_nfs = client.V1PersistentVolumeClaimVolumeSource(claim_name="pvc-nfs")
            volume_nvme = client.V1Volume(name='nvme', persistent_volume_claim=pvc_nfs)
            volumem_nvme = client.V1VolumeMount(
                            name="nvme",
                            mount_path="/nvme",
                        )

            pvc_cos = client.V1PersistentVolumeClaimVolumeSource(claim_name="geotiled-pipeline-pvc-goetiled")
            volume_cos = client.V1Volume(name='cos', persistent_volume_claim=pvc_cos)
            volumem_cos = client.V1VolumeMount(
                            name="cos",
                            mount_path="/cos",
                        )


            # We then aim to create a job that moves the data 
            name='transfer-data-'+body['metadata']['name'] 
            container=client.V1Container(image="redhat/ubi9-minimal", name="basic", command=["sh", "-c"],
                    args = ["echo", outs_str],
                    #args = ["if test -f $output; then mv $output /cos/.; fi"], #only if file exists, move it
                    volume_mounts = [volumem_nvme, volumem_cos])

            spec = client.V1PodSpec(restart_policy="Never", containers=[container], volumes=[volume_nvme, volume_cos], node_name=node)
            pod_template = client.V1PodTemplateSpec(metadata=client.V1ObjectMeta(labels={"app": "transfer"}),spec=spec)
            #pod = client.V1Pod(metadata=client.V1ObjectMeta(name=name), spec = spec)
            #obj = v1.create_namespaced_pod(namespace=body['metadata']['namespace'], body=pod)
            job_spec = client.V1JobSpec(template=pod_template, backoff_limit=4)
            job = client.V1Job(api_version="batch/v1", kind="Job", metadata=client.V1ObjectMeta(name=name), spec=job_spec)
            v1 = client.BatchV1Api()
            obj = v1.create_namespaced_job(namespace=namespace, body=job)

            #msg = f"Pod {name} created"
            #kopf.info(obj.to_dict(), reason='SomeReason', message=msg)

    
