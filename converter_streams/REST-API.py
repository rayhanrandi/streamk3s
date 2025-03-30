import logging
import os
import shutil
import tempfile
import uuid
import KEDA
import yaml
from flask import Flask, request
from systemd.journal import JournalHandler  # Import JournalHandler

import Converter
import Kubernetes
import Parser
import sommelier

from datetime import datetime as dt, timezone as tz

app = Flask(__name__)

# Configure logging to use JournalHandler
logger = logging.getLogger()
logger.setLevel(logging.INFO)
journal_handler = JournalHandler()
journal_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
journal_handler.setFormatter(formatter)
logger.addHandler(journal_handler)


@app.route('/submit', methods=['POST'])
def validate():
    content = request.json
    logger.info(content)
    dirpath = tempfile.mkdtemp(suffix=f'yamls-{dt.now(tz.utc).strftime("%Y-%m-%dT%H:%M:%S%Z")}', dir=os.getcwd())
    ff = open(dirpath + '/application_model.yaml', 'w+')
    yaml.dump(content, ff, allow_unicode=True, sort_keys=False)
    ff.close()
    if os.path.exists(dirpath + '/application_model.yaml'):
        with open(dirpath + '/application_model.yaml', 'r') as file:
             tosca_yaml = yaml.safe_load(file)
        print(tosca_yaml)        
        current_imports = tosca_yaml.get('imports')
        logger.info(current_imports)
        new_imports = ["/opt/Stream-Processing/converter_streams/"+current_imports[0]]
        tosca_yaml['imports'] = new_imports
        with open(dirpath + '/application_model.yaml', 'w+') as file:
             yaml.dump(tosca_yaml, file, sort_keys=False)
        message, isCorrect = sommelier.validation(dirpath + '/application_model.yaml')
        # TODO: make yamls persistent for debugging
        # shutil.rmtree(dirpath)
        if isCorrect:
            logger.info("Application model is correct")
            operator_list, host_list, namespace = Parser.ReadFile(content)
            namespace_file = Converter.namespace(namespace)
            persistent_volumes, deployment_files, confimap_files = Converter.tosca_to_k8s(
                operator_list, host_list,
                namespace)
            Kubernetes.apply(namespace_file)
            # write the namespace file to yaml
            ff = open(dirpath + '/namespace.yaml', 'w+')
            yaml.dump(namespace_file, ff, allow_unicode=True, sort_keys=False)
            ff.close()
            if persistent_volumes:
                for pv in persistent_volumes:
                    Kubernetes.apply(pv)
                    # write the persistent volume file to yaml
                    ff = open(dirpath + '/persistent_volume.yaml', 'w+')
                    yaml.dump(pv, ff, allow_unicode=True, sort_keys=False)
                    ff.close()
            for configmap in confimap_files:
                Kubernetes.apply(configmap)
                # write the configmap file to yaml
                ff = open(dirpath + '/configmap.yaml', 'w+')
                yaml.dump(configmap, ff, allow_unicode=True, sort_keys=False)
                ff.close()
            for deploy in deployment_files:
                Kubernetes.apply(deploy)
                # write the deployment file to yaml
                ff = open(dirpath + '/deployment.yaml', 'w+')
                yaml.dump(deploy, ff, allow_unicode=True, sort_keys=False)
                ff.close()
                os.system("kubectl wait --for condition=ready pods --all -n " + namespace + " --timeout=30s")
            KEDA.write_rules_config(operator_list)
            Converter.configure_instancemanager({"queue": "termination-queue", "namespace": namespace})
        else:
            logger.info("Application model is not correct")
    return message


if __name__ == '__main__':
    app.run(host='0.0.0.0', port='9001', debug=True)

