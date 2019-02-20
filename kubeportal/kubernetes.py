'''
    Synchronization between Kubernetes API server and portal database.

    The API server is the master data source, the portal just mirrors it.
    The only exception are newly created records in the portal, which should
    lead to according resource creation in in API server.

    Kubeportal will never delete resources in Kubernetes.
    This must be done by other means, such as kubectl.
'''

from kubernetes import client, config
import json

from kubeportal.models import KubernetesNamespace, KubernetesServiceAccount


class StupidLogger:
    logs = []

    def info(self, msg):
        self.logs.append(msg)

    def error(self, msg):
        self.logs.append(msg)

    def reset(self):
        self.logs = []


logger = StupidLogger()


def sync_namespaces(v1):
    # K8S namespaces -> portal namespaces
    k8s_ns_list = v1.list_namespace()
    k8s_ns_uids = []
    for k8s_ns in k8s_ns_list.items:
        k8s_ns_name = k8s_ns.metadata.name
        k8s_ns_uid = k8s_ns.metadata.uid
        # remember for later use
        k8s_ns_uids.append(k8s_ns_uid)
        portal_ns, created = KubernetesNamespace.objects.get_or_create(name=k8s_ns_name, uid=k8s_ns_uid)
        if created:
            # Create missing namespace record
            logger.info("Creating portal record for Kubernetes namespace '{0}'".format(k8s_ns_name))
            portal_ns.save()
        else:
            # No action needed
            logger.info("Found existing portal record for Kubernetes namespace '{0}'".format(k8s_ns_name))

    # portal namespaces -> K8S namespaces
    for portal_ns in KubernetesNamespace.objects.all():
        if portal_ns.uid:
            # Portal namespace records with UID must be given in K8S, or they are
            # stale und should be deleted
            if portal_ns.uid in k8s_ns_uids:
                # No action needed
                logger.info("Found existing Kubernetes namespace '{0}' for portal record".format(portal_ns.name))
            else:
                # Remove stale namespace record
                logger.info("Removing stale portal record for Kubernetes namespace '{0}'".format(portal_ns.name))
                portal_ns.delete()
        else:
            # Portal namespaces without UID are new and should be created in K8S
            logger.info("Creating Kubernetes namespace '{0}'".format(portal_ns.name))
            assert(False)


def sync_svcaccounts(v1):
    # K8S svc accounts -> portal svc accounts
    k8s_svca_list = v1.list_service_account_for_all_namespaces()
    print(k8s_svca_list)
    for k8s_svca in k8s_svca_list.items:
        k8s_svca_name = k8s_svca.metadata.name
        k8s_svca_ns = k8s_svca.metadata.namespace
        # Not finding the namespace record for this namespace name
        # means inconsistency - re-sync is needed anyway, so breaking
        # here is fine
        try:
            portal_ns = KubernetesNamespace.objects.get(name=k8s_svca_ns)
        except Exception:
            logger.error("Skipping {0}:{1}, namespace does not exist.".format(k8s_svca_ns, k8s_svca_name))
            continue
        k8s_svca_uid = k8s_svca.metadata.uid
        portal_svca, created = KubernetesServiceAccount.objects.get_or_create(name=k8s_svca_name, uid=k8s_svca_uid, namespace=portal_ns)
        if created:
            # Create missing service account record
            logger.info("Creating portal record for Kubernetes service account '{0}:{1}'".format(k8s_svca_ns, k8s_svca_name))
            portal_svca.save()
        else:
            # No action needed
            logger.info("Found existing portal record for Kubernetes service account '{0}:{1}'".format(k8s_svca_ns, k8s_svca_name))


def sync():
    logger.reset()
    logger.info("Starting synchronization ...")
    logger.info("Loading Kubernetes client configuration ...")
    try:
        config.load_kube_config()
        v1 = client.CoreV1Api()
        logger.info("Checking namespaces ...")
        sync_namespaces(v1)
        logger.info("Checking service accounts ...")
        sync_svcaccounts(v1)
    except client.rest.ApiException as e:
        msg = json.loads(e.body)
        logger.error("Exception: {0}".format(msg['message']))
    return logger.logs
