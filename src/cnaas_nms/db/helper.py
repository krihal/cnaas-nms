import netaddr
from typing import List, Optional

from sqlalchemy.orm.exc import NoResultFound

from cnaas_nms.db.device import Device
from cnaas_nms.db.mgmtdomain import Mgmtdomain


def canonical_mac(mac):
    """Return a standardized format of MAC-addresses for CNaaS to
    store in databases etc."""
    na_mac = netaddr.EUI(mac)
    na_mac.dialect = netaddr.mac_bare
    return str(na_mac)


def find_mgmtdomain(session, hostnames: List[str]) -> Optional[Mgmtdomain]:
    """Find the corresponding management domain for a pair of
    distribution switches.

    Args:
        hostnames: A list of two hostnames for the distribution switches

    Raises:
        ValueError: On invalid hostnames etc
    """
    if not isinstance(hostnames, list) or not len(hostnames) == 2:
        raise ValueError("hostnames argument must be a list with two device hostnames")
    for hostname in hostnames:
        if not Device.valid_hostname(hostname):
            raise ValueError(f"Argument {hostname} is not a valid hostname")
    try:
        device0 = session.query(Device).filter(Device.hostname == hostnames[0]).one()
    except NoResultFound:
        raise ValueError(f"hostname {hostnames[0]} not found in device database")
    try:
        device1 = session.query(Device).filter(Device.hostname == hostnames[1]).one()
    except NoResultFound:
        raise ValueError(f"hostname {hostnames[1]} not found in device database")
    mgmtdomain = session.query(Mgmtdomain).\
        filter(
            ((Mgmtdomain.device_a == device0) & (Mgmtdomain.device_b == device1))
            |
            ((Mgmtdomain.device_a == device1) & (Mgmtdomain.device_b == device0))
        ).one_or_none()
    return mgmtdomain
