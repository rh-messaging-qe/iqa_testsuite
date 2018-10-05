import time

from messaging_components.routers import Dispatch
from messaging_components.routers.dispatch.management import RouterQuery

from iqa_common.executor import Command, Execution

MESH_SIZE = 3


def test_scale_up_router(router_cluster: Dispatch):
    """
    Executes "oc" command to scale up the number of PODs according to value defined in MESH_SIZE constant.
    It also uses 'amq-interconnect' as the deployment config name (standard in official templates).

    Test passes if command is executed without errors.
    Note: the oc command expects that current session is logged to Openshift cluster (you can do it manually,
          but it will be also done through the CI job).
    :param router_cluster:
    :return:
    """

    cmd_scale_up = Command(args=['oc', 'scale', '--replicas=%d' % MESH_SIZE, 'dc', 'amq-interconnect'], timeout=30,
                           stderr=True, stdout=True)
    execution: Execution = router_cluster.execute(cmd_scale_up)
    execution.wait()
    assert execution.completed_successfully()


def test_router_mesh_after_scale_up(router_cluster: Dispatch):
    """
    Queries Router for all Node Entities available in the topology.
    It expects the number of nodes matches number of PODs (mesh is correctly formed).
    :param router_cluster:
    :return:
    """
    validate_mesh_size(router_cluster, MESH_SIZE)


def test_scale_down_router(router_cluster: Dispatch):
    """
    Scale down the number of PODs to 1.
    Expects that the scale down command completes successfully.
    :param router_cluster:
    :return:
    """
    cmd_scale_up = Command(args=['oc', 'scale', '--replicas=1', 'dc', 'amq-interconnect'], timeout=30)

    execution: Execution = router_cluster.execute(cmd_scale_up)
    execution.wait()

    assert execution.completed_successfully()


def test_router1_mesh_after_scale_down(router_cluster: Dispatch):
    """
    Queries the router to validate that the number of Nodes in the topology is 1.
    :param router_cluster:
    :return:
    """
    validate_mesh_size(router_cluster, 1)


def validate_mesh_size(router_cluster: Dispatch, new_size: int):
    """
    Asserts that router topology size matches "new_size" value.
    :param router_cluster:
    :param new_size:
    :return:
    """
    time.sleep(60)
    query = RouterQuery(host=router_cluster.node.ip, port=router_cluster.port, router=router_cluster)
    node_list = query.node()
    assert len(node_list) == new_size
