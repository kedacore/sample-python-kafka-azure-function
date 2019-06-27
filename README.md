# Sample tweet processor (Azure Functions + Kafka)

The following sample includes an Azure Function (written in Python) that triggers as messages arrive at a local Kafka topic.  

The Kafka topic is being populated by tweets and as the function triggers, it will populate a real-time Power BI dashboard (optional) with information on the tweet sentiment.

## Pre-requisites

The following components are necessary for this tutorial:
* Docker installed
* Kubernetes cluster
* KEDA installed on the cluster
* [Azure Functions core tools](https://github.com/azure/azure-functions-core-tools#installing)
* A [registered twitter application](https://developer.twitter.com/apps) with associated consumer key + secret and access token + secret

You will need the Kubernetes cluster to deploy the local Kafka cluster where the tweets are published to. KEDA as well as the Azure Function runtime will also be installed on this Kubernetes cluster as well.

## Objective of Sample 
The objective of this sample is to demonstrate how to horizontally scale Azure function instances (pods) running on a Kubernetes cluster based on the number of tweets available at the target Kafka topic. The objective of the tutorial is not for demonstrating how to scale the Kafka cluster. 

If you already have a running Kafka cluster, you can specify the parameters for that cluster instead and skip the deployment of the Kafka cluster components from the Confluent Helm chart.

## Setup

The below will walk you through creating a Kafka topic within your function, publishing your function to that cluster, and then publishing an agent to pull data from Twitter and publish it to Kafka.  As the events land in Kafka, the function will automatically trigger and scale.  Feel free to skip portions if they already exist in your cluster.

#### Clone the repo and navigate to it
```cli
git clone https://github.com/kedacore/sample-python-kafka-azure-function
cd sample-python-kafka-azure-function
func extensions install
```

### Create a Kafka topic in your cluster

#### [Install helm](https://helm.sh/docs/using_helm/)

#### Add the confluent helm repo

This step makes the Confluent repo available from your local Helm installation

```cli
helm repo add confluentinc https://confluentinc.github.io/cp-helm-charts/
helm repo update
```

#### Deploy the Confluent Kafka helm chart

The Confluent Helm chart contains the following 7 components necessary to spin up a Kafka cluster:
- cp-control-center (used for monitoring and management by developers and operations teams)
- cp-kafka-connect (used for pushing data to and pull data out of kafka brokers)
- cp-kafka-rest (provides universal access to Kafka cluster from any network connected device via HTTP)
- cp-kafka (kafka brokers where data is stored)
- cp-ksql-server (provides capabilities for stream processing against Kafka brokers using SQL-like semantics)
- cp-schema-registry (provides a central registry for the format of Kafka data to guarantee compatibility)
- cp-zookeeper (a centralized service providing a hierarchical key-value store for managing cluster metadata)

Your installation disables the schema registry, rest proxy and connect components but enables the remaining components listed above

```cli
helm install --name kafka --set cp-schema-registry.enabled=false,cp-kafka-rest.enabled=false,cp-kafka-connect.enabled=false,dataLogDirStorageClass=default,dataDirStorageClass=default,storageClass=default confluentinc/cp-helm-charts
```
You'll need to wait for the deployment to complete before continuing.  This may take a few minutes to spin up all the stateful sets.

#### Deploy a kafka client pod with configuration

This is the client that will push data into the Kafka cluster

```cli
kubectl apply -f deploy/kafka-client.yaml
```
#### Log into the Kafka client

Connect to the Kafka client pod using bash

```cli
kubectl exec -it kafka-client -- /bin/bash
```

#### Create a kafka topic

Create a local Kafka topic that the messages will be published to. As messages arrive at this topic, the KEDA platform will scale the azure function instances accordingly.

```cli
kafka-topics --zookeeper kafka-cp-zookeeper-headless:2181 --topic twitter --create --partitions 5 --replication-factor 1 --if-not-exists

exit
```

### Deploying the function app

#### Deploy the function app

```cli
func kubernetes deploy --name twitter-function --registry <docker-hub-username>
```

Alternatively, you can build and publish the image on your own and provide the `--image-name` instead of the `--registry`

#### Validate the function is deployed

```cli
kubectl get deploy
```

You should see the `twitter-function` is deployed, but since there are no Twitter events it has 0 replicas.

### Feed twitter data

#### Setup twitter consumer

Open the `./deploy/twitter-to-kafka.yaml` file and replace the environment variables near the bottom of the deployment with your own values:

|Name|Description|Example|
|--|--|--|
|TWITTER_STREAMING_MODE|Streaming mode for tweepy|normal|
|KAFKA_ENDPOINT|Kafka endpoint to publish|kafka-cp-kafka-headless:9092|
|CONSUMER_KEY|Twitter app consumer key|MGxxxxxxxx|
|CONSUMER_SECRET|Twitter app consumer secret|RBpw98sxukm3kKYxxxxx|
|ACCESS_TOKEN|Twitter app access token|126868398-2uGxxxxxx|
|ACCESS_TOKEN_SECRET|Twitter app access token secret|oqiewyaPj0QFDk3Xl2Pxxxxx|
|KAFKA_TOPIC|Kafka topic to publish|twitter|
|SEARCH_TERM|Twitter search term|Avengers|

Save the changes

#### Deploy the twitter consumer

```cli
kubectl apply -f deploy/twitter-to-kafka.yaml
```

### Validate and view outputs

#### View the current deployments

As the twitter consumer spins up it should start emitting data.  You should then see the `twitter-function` get 1 or more instances.  The scale-out can be adjusted by modifying how many messages each instance will pull at once (defined in the `host.json` file of the function), or the `lagThreshold` of the created `ScaledObject` in Kubernetes.

```cli
# View the current Kubernetes deployments
kubectl get deploy

# View the logs of function pods
kubectl get pods
kubectl logs twitter-function-<some-pod-Id>
```

You should see logs streaming with tweet data and sentiment scores:

```bash
info: Function.KafkaTwitterTrigger.User[0]
      Tweet analyzed
      Tweet text: RT @ballerguy: Yeah avengers endgame was good but I found out my boyfriend is a movie clapper so at what cost
      Sentiment: 0.09523809523809523
info: Function.KafkaTwitterTrigger[0]
      Executed 'Functions.KafkaTwitterTrigger' (Succeeded, Id=67cc49a3-0e13-4fa8-b605-a041ce37420a)
info: Host.Triggers.Kafka[0]
      Stored commit offset twitter / [3] / 37119
```

## Clean up resources

Once you are done with the tutorial, you can run the following commands to clean up resources created as part of this sample:

```cli
kubectl delete deploy/twitter-to-kafka-deployment
kubectl delete deploy/twitter-function
kubectl delete ScaledObject/twitter-function
kubectl delete Secret/twitter-function
kubectl delete pod kafka-client
helm delete kafka
```
