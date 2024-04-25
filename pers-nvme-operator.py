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

@kopf.on.update('pipelinerun')
def track_pipelineruns(body, **kwargs):
    logging.info(f"Pipeline {body['status']['conditions'][0]['reason']} and {body['status']['conditions'][0]['status']}")
    while not body['status']['conditions'][0]['reason'] == 'Succeeded':
        #logging.info(f"Pipeline running")
    else:
        logging.info(f"Pipeline stopped")



@kopf.on.update('Pod',
        labels={'app.kubernetes.io/managed-by': 'tekton-pipelines'})
def track_tasks(body, **kwargs):

    # Watching the statuses of all pods
    logging.info(f"{list(body['status']['containerStatuses'][0]['state'].keys())[0]}")
    # Check if the pod completes
    if list(body['status']['containerStatuses'][0]['state'].keys())[0]=='terminated': 
        message=body['status']['containerStatuses'][0]['state']['terminated']['message']
        m_dict=list(eval(message))
        # Check if the pod has an output (task pod) or if it has a manifest (pvc creation pod)
        if m_dict[0]['key']=='Output':
            # If it's a task pod we aim to gather the name of the pod, the node, and the output data generated

            # Information about the pod
            # Podname and outputs
            logging.info(f"The name of the pod is {body['metadata']['name']} and its output is {m_dict[0]['value']}")
            # Extract annotations and turn them from str to dict
            annotations = json.loads(body['metadata']['annotations']['kopf.zalando.org/last-handled-configuration'])
            # Volumes related to the application --OO hardcoded to nvme and cos in this case
            logging.info(f"{len(annotations['spec']['volumes'])} volumes in the pod {annotations['spec']['volumes'][9:11]}")
            # Get the nodename
            node = annotations['spec']['nodeName']

            # Insert entry in database
            connection.execute("INSERT INTO pods (podname, node, outputs, pushed) VALUES(?, ?, ?, ?)",
                                                  (body['metadata']['name'], node, m_dict[0]['value'], "False"))
            connection.commit()
     

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


            # We then aim to create a pod 
            name='transfer-data-'+body['metadata']['name'] 
            container=client.V1Container(image="redhat/ubi9-minimal", name="basic", args=["mv", "],
                    volume_mounts = [volumem_nvme, volumem_cos])

            spec = client.V1PodSpec(containers=[container], volumes=[volume_nvme, volume_cos], node_name=node)
            pod = client.V1Pod(metadata=client.V1ObjectMeta(name=name), spec = spec)
            obj = v1.create_namespaced_pod(namespace=body['metadata']['namespace'], body=pod)

            msg = f"Pod {name} created"
            kopf.info(obj.to_dict(), reason='SomeReason', message=msg)

    
