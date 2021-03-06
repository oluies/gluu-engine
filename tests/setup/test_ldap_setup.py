import pytest


@pytest.mark.skip(reason="rewrite needed")
def test_setup(ldap_setup, db, provider, patched_run,
               patched_sleep, patched_exec_cmd):
    # TODO: it might be better to split the tests
    db.persist(provider, "providers")
    ldap_setup.setup()


@pytest.mark.skip(reason="rewrite needed")
def test_setup_with_replication(ldap_setup, db, cluster, provider,
                                patched_sleep, patched_exec_cmd,
                                patched_run):
    from gluuengine.model import LdapNode
    from gluuengine.model import STATE_SUCCESS

    db.persist(provider, "providers")

    peer_node = LdapNode()
    peer_node.provider_id = provider.id
    peer_node.cluster_id = cluster.id
    peer_node.state = STATE_SUCCESS
    db.persist(peer_node, "nodes")
    db.update(ldap_setup.cluster.id, ldap_setup.cluster, "clusters")

    # TODO: it might be better to split the tests
    assert ldap_setup.setup()


@pytest.mark.skip(reason="rewrite needed")
def test_after_setup(cluster, ldap_setup, provider, db,
                     patched_sleep, patched_exec_cmd):
    from gluuengine.model import OxauthNode
    from gluuengine.model import OxtrustNode
    from gluuengine.model import OxidpNode
    from gluuengine.model import STATE_SUCCESS

    db.persist(cluster, "clusters")
    db.persist(provider, "providers")

    oxauth = OxauthNode()
    oxauth.id = "auth-123"
    oxauth.cluster_id = cluster.id
    oxauth.provider_id = provider.id
    oxauth.state = STATE_SUCCESS
    db.persist(oxauth, "nodes")

    oxtrust = OxtrustNode()
    oxtrust.id = "trust-123"
    oxtrust.cluster_id = cluster.id
    oxtrust.provider_id = provider.id
    oxtrust.state = STATE_SUCCESS
    db.persist(oxtrust, "nodes")

    oxidp = OxidpNode()
    oxidp.id = "idp-123"
    oxidp.cluster_id = cluster.id
    oxidp.provider_id = provider.id
    oxidp.state = STATE_SUCCESS
    db.persist(oxidp, "nodes")

    db.update(ldap_setup.cluster.id, ldap_setup.cluster, "clusters")
    ldap_setup.node.state = STATE_SUCCESS
    db.persist(ldap_setup.node, "nodes")
    ldap_setup.after_setup()


@pytest.mark.skip(reason="rewrite needed")
def test_teardown(ldap_setup, cluster, provider, oxauth_node, db,
                  patched_sleep, patched_exec_cmd, patched_run):
    db.persist(cluster, "clusters")
    db.persist(provider, "providers")
    oxauth_node.state = "SUCCESS"
    db.persist(oxauth_node, "nodes")
    ldap_setup.teardown()


@pytest.mark.skip(reason="rewrite needed")
def test_teardown_with_replication(ldap_setup, cluster, db, patched_run,
                                   patched_sleep, patched_exec_cmd):
    from gluuengine.model import LdapNode
    from gluuengine.model import STATE_SUCCESS

    node1 = LdapNode()
    node1.id = "ldap-123"
    node1.cluster_id = cluster.id
    node1.state = STATE_SUCCESS
    db.persist(node1, "nodes")

    node2 = LdapNode()
    node2.id = "ldap-456"
    node2.cluster_id = cluster.id
    node2.state = STATE_SUCCESS
    db.persist(node2, "nodes")

    db.update(ldap_setup.cluster.id, ldap_setup.cluster, "clusters")
    ldap_setup.teardown()


@pytest.mark.skip(reason="rewrite needed")
def test_replicate_from(ldap_setup, db, provider, patched_run,
                        patched_sleep, patched_exec_cmd):
    from gluuengine.model import LdapNode
    from gluuengine.model import STATE_SUCCESS

    db.persist(provider, "providers")
    peer_node = LdapNode()
    peer_node.id = "ldap-123"
    peer_node.provider_id = provider.id
    peer_node.state = STATE_SUCCESS
    db.persist(peer_node, "nodes")

    db.update(ldap_setup.cluster.id, ldap_setup.cluster, "clusters")
    ldap_setup.replicate_from(peer_node)


@pytest.mark.skip(reason="rewrite needed")
def test_notify_ox(ldap_setup, db, oxidp_node,
                   patched_sleep, patched_exec_cmd):
    from gluuengine.model import STATE_SUCCESS

    oxidp_node.state = STATE_SUCCESS
    db.persist(oxidp_node, "nodes")
    ldap_setup.notify_ox()


@pytest.mark.skip(reason="rewrite needed")
def test_after_setup_modify_config(cluster, ldap_setup,
                                   patched_sleep, patched_exec_cmd):
    from gluuengine.database import db
    from gluuengine.model import LdapNode
    from gluuengine.model import STATE_SUCCESS

    db.persist(cluster, "clusters")

    ldap = LdapNode()
    ldap.id = "ldap-123"
    ldap.cluster_id = cluster.id
    ldap.state = STATE_SUCCESS
    db.persist(ldap, "nodes")

    db.update(ldap_setup.cluster.id, ldap_setup.cluster, "clusters")
    ldap_setup.node.state = "SUCCESS"
    db.persist(ldap_setup.node, "nodes")
    ldap_setup.after_setup()
