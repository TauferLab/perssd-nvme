import kopf
import logging
from kubernetes import client, config, watch
from python_settings import settings
import json
import sqlite3
from sqlite3 import Error
import pandas as pd
import itertools 

# DAG Functions
def from_parents_to_children(dag_dict):
    all_tasks = list(dag_dict.keys())
    dag = {task: [] for task in all_tasks}
    for a, b in itertools.permutations(all_tasks, 2):
        if any(d['parent_task'] == a for d in dag_dict[b]):
            dag[a].append(b)
    return(dag)

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
      taskname TEXT NOT NULL,
      node TEXT,
      children INTEGER,
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

def verify_pod(connection, namespace):
    df = pd.read_sql_query("SELECT * from pods", connection)
    not_pushed = df.loc[df['pushed'] == "False"].reset_index(drop=True)
    for p, pod in enumerate(not_pushed['podname']):
        #logging.info(f"POD: {pod} \n DATAFRAME: {not_pushed}")
        children = not_pushed.loc[p, 'children'].split(" ")
        #logging.info(f"POD CHECKING {pod} and {children} and CHILDREN 0 {children[0]=='' }")
        if set(children).issubset(df['taskname'].tolist()) or children[0]=='':
            logging.info(f"READY TO BE PUSHED: {pod}")
            condition = 'UPDATE pods SET pushed=? WHERE podname = ?'
            connection.cursor().execute(condition, ("True", pod))
            connection.commit()
            transfer_data(pod, not_pushed.loc[p,'outputs'], not_pushed.loc[p,'node'], namespace)
            logging.info(f"DATA PUSHED {not_pushed.loc[p,'outputs']} FROM {pod}")

def transfer_data(pod_name, outs_str, node, namespace):
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
    name='transfer-data-'+pod_name
    security_context = client.V1SecurityContext(privileged=True, run_as_user=0)
    container=client.V1Container(image="redhat/ubi9-minimal", name="basic", command=["sh", "-c"],
            args = [f"for f in {outs_str}; do if test -f $f; then echo $f FILE MOVED && mv $f /cos/.; else echo $f DIR moved && mv $f/ /cos/.; fi; done;"], #only if file exists, move it
            volume_mounts = [volumem_nvme, volumem_cos], security_context=security_context)
    
    spec = client.V1PodSpec(restart_policy="Never", containers=[container], volumes=[volume_nvme, volume_cos])#, node_name=node)
    pod_template = client.V1PodTemplateSpec(metadata=client.V1ObjectMeta(labels={"app": "transfer"}),spec=spec)
    job_spec = client.V1JobSpec(template=pod_template, backoff_limit=4)
    job = client.V1Job(api_version="batch/v1", kind="Job", metadata=client.V1ObjectMeta(name=name), spec=job_spec)
    v1 = client.BatchV1Api()
    obj = v1.create_namespaced_job(namespace=namespace, body=job)

@kopf.on.update('Pod',
        labels={'app.kubernetes.io/managed-by': 'tekton-pipelines'})
def track_tasks(body, **kwargs):
    
    # Start k8s client
    #v1 = client.CoreV1Api()

    # Watching the statuses of all pods
    namespace = body['metadata']['namespace']
    pod_name = body['metadata']['name']
    logging.info(f"POD {body['metadata']['name']}")
    #logging.info(f"STATUS {body['status']['containerStatuses'][0]['state'].keys()}")


    # Check if the pod completes
    if list(body['status']['containerStatuses'][0]['state'].keys())[0]=='terminated': 
        if body['status']['containerStatuses'][0]['state']['terminated']['reason']=='Completed':

            message=body['status']['containerStatuses'][0]['state']['terminated']['message']
            outputs=list(eval(message))
            # Check if the pod has an output (task pod) or if it has a manifest (pvc creation pod)
            outs_list=[]
            if outputs[0]['key'] != 'manifest':

                # Initialize DAG
                ## Read sqlite as dataframe
                df = pd.read_sql_query("SELECT * from pods", connection)
                #logging.info(f"DATAFRAME {df.head()}")

                ## This relies upon the idea that the first task in the workflow is creating a PVC for COS or NVMe-NFS
                ## THIS SHOULD BE ATOMIC
                if len(df) == 0:
                    global dag_dict
                    dag_dict = json.loads(body['metadata']['annotations']['tekton.dev/input_artifacts'])
                    dag_dict = from_parents_to_children(dag_dict)

                # Get the children for that pod
                task_name = body['metadata']['labels']['tekton.dev/pipelineTask']
                children =  dag_dict[task_name]


                # Get the outputs
                [outs_list.append(x['value']) for x in outputs[:-1]]
                outs_str = " ".join(outs_list)
                # Extract annotations and turn them from str to dict
                annotations = json.loads(body['metadata']['annotations']['kopf.zalando.org/last-handled-configuration'])
                # Volumes related to the application --OO hardcoded to nvme and cos in this case
                #logging.info(f"{len(annotations['spec']['volumes'])} volumes in the pod {annotations['spec']['volumes'][9:11]}")
                # Get the nodename
                node = annotations['spec']['nodeName']

                # Insert entry in database
                connection.execute("INSERT INTO pods (podname, taskname, node, children, outputs, pushed) VALUES(?, ?, ?, ?, ?, ?)",
                                                      (pod_name, task_name, node, " ".join(children),  outs_str, "False"))
                connection.commit()

                # Check pods and transfer data as needed
                verify_pod(connection, namespace)



    
