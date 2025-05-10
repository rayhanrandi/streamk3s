echo "--------------------------------------------"
echo "Installing Stream Processing Platform"
echo "--------------------------------------------"
echo "--------------------------------------------"
echo "Requirements"
echo "--------------------------------------------"
apt update
apt install snapd
apt-get install python3.6
apt install python3-pip
sudo apt install pkg-config
sudo apt install libsystemd-dev
sudo -H pip3 install oyaml
sudo -H pip3 install hurry.filesize
sudo -H pip3 install PyYAML
sudo -H pip3 install flask[async]
sudo -H pip3 install tosca-parser
sudo -H pip3 install pika
sudo -H pip3 install tenacity
sudo -H pip3 install python-dotenv
sudo -H pip3 install systemd-python
snap install helm --classic
echo "--------------------------------------------"
echo "RabbitMQ"
echo "--------------------------------------------"
helm repo add stable https://charts.helm.sh/stable
kubectl config view --raw > ~/.kube/config
kubectl create namespace rabbit
helm install mu-rabbit stable/rabbitmq --namespace rabbit --set rabbitmqVhost=streams
kubectl wait --namespace rabbit --for condition=ready pod/mu-rabbit-rabbitmq-0 --timeout=120s
kubectl expose -n rabbit pod mu-rabbit-rabbitmq-0 --port=15672 --target-port=15672 --name=loadbalancer --type=LoadBalancer
echo "--------------------------------------------"
echo "NodeRED"
echo "--------------------------------------------"
mkdir /opt/NodeRED
kubectl apply -f nodered-namespace.yaml
kubectl apply -f nodered-pv.yaml
kubectl apply -f nodered-pvc.yaml
kubectl apply -f nodered-deployment.yaml
name=$(kubectl get pods -n gui -o jsonpath='{.items[0].metadata.name}')
kubectl wait --namespace gui --for condition=ready pod/$name --timeout=120s
kubectl expose -n gui pod  $name --port=1880 --target-port=1880 --name=loadbalancer --type=LoadBalancer
nodered_ip=$(kubectl get pod $name -n gui -o jsonpath='{.status.podIP}')
sleep 60
curl -XPUT -H "Content-type: application/json" --data-binary "@main-subflow.json" "http://${nodered_ip}:1880/flow/global"
echo "--------------------------------------------"
echo "KEDA"
echo "--------------------------------------------"
# Without admission webhooks
kubectl apply --server-side -f https://github.com/kedacore/keda/releases/download/v2.12.0/keda-2.12.0-core.yaml
echo "--------------------------------------------"
echo "Instance Manager"
echo "--------------------------------------------"
RABBITMQ_USERNAME="user"
RABBITMQ_PASSWORD=$(kubectl get secret mu-rabbit-rabbitmq --namespace rabbit -o jsonpath='{.data.rabbitmq-password}' | base64 --decode)
# Create .env file and store the credentials
pod_ip=$(kubectl get pod mu-rabbit-rabbitmq-0 -n rabbit -o jsonpath='{.status.podIP}')
node_port=$(kubectl get svc loadbalancer -n rabbit -o jsonpath='{.spec.ports[0].nodePort}')
cd ..
cd instancemanager
echo "RABBITMQ_USERNAME=$RABBITMQ_USERNAME" > .env
echo "RABBITMQ_PASSWORD=$RABBITMQ_PASSWORD" >> .env
if [ -n "$pod_ip" ]; then
    # Create .env file and store the pod IP address
    echo "POD_IP=$pod_ip" >> .env
    echo "Pod IP Address found: $pod_ip"
else
    # If pod IP address is not found, display a message
    echo "Pod IP Address not found for RabbitMQ."
fi
if [ -n "$node_port" ]; then
    # Create .env file and store rabbit node port
    echo "NODE_PORT=$node_port" >> .env
    echo "Node Port for RabbitMQ LB found: $node_port"
else
    # If node port is not found, display a message
    echo "Node Port not found for RabbitMQ."
fi
cd ..
cp instancemanager/.env converter_streams
cd instancemanager
cd ..
mkdir /opt/Stream-Processing/
cp -r instancemanager /opt/Stream-Processing
cd installation
cp instancemanager.service /etc/systemd/system/
systemctl enable instancemanager.service
systemctl start instancemanager.service
echo "--------------------------------------------"
echo "Converter"
echo "--------------------------------------------"
cd ..
cp -r converter_streams /opt/Stream-Processing
cd installation
cp converter.service /etc/systemd/system/
cp rabbitmq_startup.sh /usr/local/bin/
cp wait_and_run_rabbitmq.sh /usr/local/bin
systemctl enable converter.service
systemctl start converter.service
