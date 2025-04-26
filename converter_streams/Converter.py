import json
import os
import logging
import Host
import Kubernetes
from hurry.filesize import size, iec
import subprocess
import requests
from systemd.journal import JournalHandler
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
log = logging.getLogger("Converter")
log.addHandler(JournalHandler())
log.setLevel(logging.INFO)


def create_volumes(pod_name, disk_size, namespace):
    pv = {
        "apiVersion": "v1",
        "kind": "PersistentVolume",
        "metadata": {"name": pod_name + "-pv", "namespace": namespace},
        "spec": {
            "capacity": {"storage": disk_size},
            "accessModes": ["ReadWriteOnce"],
            "persistentVolumeReclaimPolicy": "Retain",
            "storageClassName": "local-path",
            "hostPath": {"path": "/mnt/data"},
        },
    }
    pvc = {
        "apiVersion": "v1",
        "kind": "PersistentVolumeClaim",
        "metadata": {
            "name": pod_name + "-pvc",
            "namespace": namespace,
        },
        "spec": {
            "accessModes": ["ReadWriteOnce"],
            "resources": {
                "requests": {
                    "storage": disk_size,
                },
            },
            "storageClassName": "local-path",
        },
    }

    return pv, pvc


def create_deployments(
    pod_name,
    namespace,
    application_label,
    order,
    image_name,
    resource_yaml,
    disk,
    os,
    node_arch,
    persistent_volume,
    port_yaml,
):
    if not persistent_volume:
        deployment = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": pod_name,
                "namespace": namespace,
                "labels": {"app": application_label},
            },
            "spec": {
                "selector": {"matchLabels": {"app": application_label}},
                "strategy": {"type": "Recreate"},
                "template": {
                    "metadata": {"labels": {"app": application_label}},
                    "spec": {
                        "containers": [
                            {
                                "name": "companion-container",
                                "image": "kevinmarcellius/companion:v1.0",
                                "imagePullPolicy": "IfNotPresent",
                                "env": [
                                    {
                                        "name": "MY_POD_IP",
                                        "valueFrom": {
                                            "fieldRef": {"fieldPath": "status.podIP"}
                                        },
                                    },
                                    {
                                        "name": "MY_POD_NAME",
                                        "valueFrom": {
                                            "fieldRef": {"fieldPath": "metadata.name"}
                                        },
                                    },
                                ],
                                "ports": [
                                    {"containerPort": 4321, "name": "publishport"}
                                ],
                                "volumeMounts": [
                                    {
                                        "name": "cache-volume",
                                        "mountPath": "volume" + order,
                                    }
                                ],
                                "envFrom": [
                                    {"configMapRef": {"name": "publishconfig-" + order}}
                                ],
                            },
                            {
                                "name": pod_name,
                                "resources": resource_yaml,
                                "image": image_name,
                                "imagePullPolicy": "IfNotPresent",
                                "env": [
                                    {
                                        "name": "MY_POD_IP",
                                        "valueFrom": {
                                            "fieldRef": {"fieldPath": "status.podIP"}
                                        },
                                    },
                                    {
                                        "name": "MY_POD_NAME",
                                        "valueFrom": {
                                            "fieldRef": {"fieldPath": "metadata.name"}
                                        },
                                    },
                                    {
                                        "name": "MY_POD_NAMESPACE",
                                        "valueFrom": {
                                            "fieldRef": {
                                                "fieldPath": "metadata.namespace"
                                            }
                                        },
                                    },
                                ],
                                "ports": port_yaml,
                                "envFrom": [
                                    {"configMapRef": {"name": "appconfig-" + order}}
                                ],
                            },
                        ],
                        "volumes": [
                            {"name": "cache-volume", "emptyDir": {"sizeLimit": disk}}
                        ],
                        "nodeSelector": {
                            "beta.kubernetes.io/os": os,
                            "beta.kubernetes.io/arch": node_arch,
                        },
                    },
                },
            },
        }
    else:
        deployment = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": pod_name,
                "namespace": namespace,
                "labels": {"app": application_label},
            },
            "spec": {
                "selector": {"matchLabels": {"app": application_label}},
                "strategy": {"type": "Recreate"},
                "template": {
                    "metadata": {"labels": {"app": application_label}},
                    "spec": {
                        "containers": [
                            {
                                "name": "companion-container",
                                "image": "kevinmarcellius/companion:v1.0",
                                "imagePullPolicy": "IfNotPresent",
                                "env": [
                                    {
                                        "name": "MY_POD_IP",
                                        "valueFrom": {
                                            "fieldRef": {"fieldPath": "status.podIP"}
                                        },
                                    },
                                    {
                                        "name": "MY_POD_NAME",
                                        "valueFrom": {
                                            "fieldRef": {"fieldPath": "metadata.name"}
                                        },
                                    },
                                ],
                                "ports": [
                                    {"containerPort": 4321, "name": "publishport"}
                                ],
                                "volumeMounts": [
                                    {
                                        "name": "cache-volume",
                                        "mountPath": "volume" + order,
                                    }
                                ],
                                "envFrom": [
                                    {"configMapRef": {"name": "publishconfig-" + order}}
                                ],
                            },
                            {
                                "name": pod_name,
                                "resources": resource_yaml,
                                "image": image_name,
                                "volumeMounts": [
                                    {
                                        "mountPath": "/opt/model/",
                                        "name": pod_name + "-volume",
                                    }
                                ],
                                "imagePullPolicy": "IfNotPresent",
                                "env": [
                                    {
                                        "name": "MY_POD_IP",
                                        "valueFrom": {
                                            "fieldRef": {"fieldPath": "status.podIP"}
                                        },
                                    },
                                    {
                                        "name": "MY_POD_NAME",
                                        "valueFrom": {
                                            "fieldRef": {"fieldPath": "metadata.name"}
                                        },
                                    },
                                    {
                                        "name": "MY_POD_NAMESPACE",
                                        "valueFrom": {
                                            "fieldRef": {
                                                "fieldPath": "metadata.namespace"
                                            }
                                        },
                                    },
                                ],
                                "ports": port_yaml,
                                "envFrom": [
                                    {"configMapRef": {"name": "appconfig-" + order}}
                                ],
                            },
                        ],
                        "volumes": [
                            {"name": "cache-volume", "emptyDir": {"sizeLimit": disk}},
                            {
                                "name": pod_name + "-volume",
                                "persistentVolumeClaim": {
                                    "claimName": pod_name + "-pvc"
                                },
                            },
                        ],
                        "nodeSelector": {
                            "beta.kubernetes.io/os": os,
                            "beta.kubernetes.io/arch": node_arch,
                        },
                    },
                },
            },
        }
    return deployment


def convert_bytes(bytes):
    output = 0
    if "MB" in bytes:
        number = bytes.replace("MB", "")
        output = int(number) * 1024 * 1024
    if "GB" in bytes:
        number = bytes.replace("GB", "")
        output = int(number) * 1024 * 1024 * 1024
    return output


def tosca_to_k8s(operator_list, host_list, namespace_pack):
    deployment_files = []
    persistent_volumes = []
    configmap_list = []

    for x in host_list:
        for y in operator_list:
            port_yaml = []
            if y.get_host() == x.get_name():
                persistent_volume = y.get_persistent_volume()
                logging.info(persistent_volumes)
                mem_size = convert_bytes(x.get_ram())
                kube_ram = size(mem_size, system=iec)
                disk_size = convert_bytes(x.get_disk())
                kube_disk = size(disk_size, system=iec)
                pod_name = y.get_name()
                if x.get_arch() == "x86_64":
                    node_arch = "amd64"
                if not persistent_volume:
                    resource_yaml = {
                        "limits": {
                            "cpu": x.get_cpu(),
                            "memory": kube_ram,
                            "ephemeral-storage": kube_disk,
                        }
                    }
                if persistent_volume:
                    resource_yaml = {"limits": {"cpu": x.get_cpu(), "memory": kube_ram}}
                    pv, pvc = create_volumes(pod_name, kube_disk, namespace_pack)
                    persistent_volumes.append(pv)
                    persistent_volumes.append(pvc)
                ip = os.getenv("POD_IP", "ip")
                ip = "mu-rabbit-rabbitmq.rabbit.svc.cluster.local"
                password = os.getenv("RABBITMQ_PASSWORD", "password")
                queues = y.get_queues()
                properties = queues.get("properties")
                input_queue = properties.get("input_queue")
                output_queue = properties.get("output_queue")
                order = y.get_order()
                variables = y.get_variables()

                configmap_list = generate_configmaps(
                    input_queue,
                    output_queue,
                    order,
                    namespace_pack,
                    ip,
                    password,
                    variables,
                    configmap_list,
                )
                ports = y.get_port()
                i = 0
                for port in ports:
                    i = i + 1
                    content = {
                        "containerPort": int(port),
                        "name": y.get_name() + str(i),
                    }
                    port_yaml.append(content)
                application_label = y.get_application()
                image_name = y.get_image()
                operating_system = x.get_os()
                order = str(y.get_order())
                deployment = create_deployments(
                    pod_name,
                    namespace_pack,
                    application_label,
                    order,
                    image_name,
                    resource_yaml,
                    kube_disk,
                    operating_system,
                    node_arch,
                    persistent_volume,
                    port_yaml,
                )

                deployment_files.append(deployment)
    generate_queue("termination-queue", namespace_pack)
    return persistent_volumes, deployment_files, configmap_list


def secret_generation(json, application):
    secret = {
        "apiVersion": "v1",
        "kind": "Secret",
        "metadata": {
            "name": application + "-registry-credentials",
            "namespace": application,
        },
        "type": "kubernetes.io/dockerconfigjson",
        "data": {".dockerconfigjson": json},
    }
    return secret


def namespace(application):
    namespace = {
        "apiVersion": "v1",
        "kind": "Namespace",
        "metadata": {"name": application},
    }
    password = os.getenv("RABBITMQ_PASSWORD", "password")
    ip = os.getenv("POD_IP", "ip")
    node_port = os.getenv("NODE_PORT", "node_port")
    # SOLVED: rabbitmq loadbalancer service expose the 30298 port, forward to 15672
    # SOLVED : can use localhost as ip
    command = (
        "curl -u user:"
        + password
        + " -X PUT "
        + "localhost"
        + f":{node_port}/api/vhosts/"
        + application
    )
    # curl -u user:xw -X PUT http://localhost:30298/api/vhosts/axl2
    print(str(command))
    subprocess.call([str(command)], shell=True)

    return namespace


def generate_queue(queue, application):
    password = os.getenv("RABBITMQ_PASSWORD", "password")
    parameters = {"durable": True}
    ip = os.getenv("POD_IP", "ip")
    node_port = os.getenv("NODE_PORT", "node_port")
    # SOLVED: rabbitmq loadbalancer service expose the 30298 port, forward to 15672
    # SOLVED : can use localhost as ip
    command = (
        "curl -u user:"
        + password
        + " -X PUT "
        + "localhost"
        + f":{node_port}/api/queues/"
        + application
        + "/"
        + queue
        + " --data "
        + "'"
        + json.dumps(parameters)
        + "'"
    )
    # curl -u user:xw -X PUT http://localhost:30298/api/queues/axl2/simpleq --data '{"durable":true}'
    print(str(command))
    subprocess.call([str(command)], shell=True)


def configure_instancemanager(message_dict):
    response = requests.post("http://0.0.0.0:4004/init", json=message_dict)
    if response.status_code == 200:
        print("Instancemanager is configured successfully!")
    else:
        print("Instancemanager is not configured, status code:", response.status_code)


def generate_configmaps(
    input_queue,
    output_queue,
    order,
    namespace_pack,
    ip,
    password,
    variables,
    configmap_list,
):
    if input_queue is not None and output_queue is not None:
        operator_configmap = {
            "kind": "ConfigMap",
            "apiVersion": "v1",
            "metadata": {
                "name": "appconfig-" + str(order),
                "namespace": namespace_pack,
            },
            "data": {
                "API_PORT": "4321",
                "PUBLISH_PATH": "/post_message",
                "CONSUME_PATH": "/get_message",
            },
        }
        publish_configmap = {
            "kind": "ConfigMap",
            "apiVersion": "v1",
            "metadata": {
                "name": "publishconfig-" + str(order),
                "namespace": namespace_pack,
            },
            "data": {
                "OPERATOR_PORT": "4322",
                "OPERATOR_PATH": "/post_message",
                "RABBIT_IP": ip,
                "RABBITMQ_PASSWORD": password,
                "INPUT_QUEUE": input_queue,
                "OUTPUT_QUEUE": output_queue,
                "TERMINATION_QUEUE": "termination-queue",
                "APPLICATION": namespace_pack,
            },
        }
        generate_queue(input_queue, namespace_pack)
        generate_queue(output_queue, namespace_pack)
    if input_queue is not None and output_queue is None:
        operator_configmap = {
            "kind": "ConfigMap",
            "apiVersion": "v1",
            "metadata": {
                "name": "appconfig-" + str(order),
                "namespace": namespace_pack,
            },
            "data": {
                "API_PORT": "4321",
                "CONSUME_PATH": "/get_message",
            },
        }
        publish_configmap = {
            "kind": "ConfigMap",
            "apiVersion": "v1",
            "metadata": {
                "name": "publishconfig-" + str(order),
                "namespace": namespace_pack,
            },
            "data": {
                "OPERATOR_PORT": "4322",
                "OPERATOR_PATH": "/post_message",
                "RABBIT_IP": ip,
                "RABBITMQ_PASSWORD": password,
                "INPUT_QUEUE": input_queue,
                "TERMINATION_QUEUE": "termination-queue",
                "APPLICATION": namespace_pack,
            },
        }

    if output_queue is not None and input_queue is None:
        operator_configmap = {
            "kind": "ConfigMap",
            "apiVersion": "v1",
            "metadata": {
                "name": "appconfig-" + str(order),
                "namespace": namespace_pack,
            },
            "data": {
                "API_PORT": "4321",
                "PUBLISH_PATH": "/post_message",
            },
        }

        publish_configmap = {
            "kind": "ConfigMap",
            "apiVersion": "v1",
            "metadata": {
                "name": "publishconfig-" + str(order),
                "namespace": namespace_pack,
            },
            "data": {
                "OPERATOR_PORT": "4322",
                "OPERATOR_PATH": "/post_message",
                "RABBIT_IP": ip,
                "RABBITMQ_PASSWORD": password,
                "TERMINATION_QUEUE": "termination-queue",
                "OUTPUT_QUEUE": output_queue,
                "APPLICATION": namespace_pack,
            },
        }

        generate_queue(output_queue, namespace_pack)
    # add custom env variables
    if variables:
        for key, value in variables.items():
            operator_configmap["data"][key] = value

    configmap_list.append(publish_configmap)
    configmap_list.append(operator_configmap)

    return configmap_list
