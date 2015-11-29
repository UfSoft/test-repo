# -*- coding: utf-8 -*-
'''
    :codeauthor: :email:`Pedro Algarvio (pedro@algarvio.me)`
    :copyright: © 2015 by the SaltStack Team, see AUTHORS for more details.
    :license: Apache 2.0, see LICENSE for more details.


    pytestsalt.fixtures.ports
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    Pytest salt plugin ports fixtures
'''

# Import python libs
from __future__ import absolute_import

# Import 3rd-party libs
import pytest

# Import pytestsalt libs
from pytestsalt.utils import get_unused_localhost_port


@pytest.fixture
def master_publish_port():
    '''
    Returns an unused localhost port for the master publish interface
    '''
    return get_unused_localhost_port()


@pytest.fixture
def master_return_port():
    '''
    Returns an unused localhost port for the master return interface
    '''
    return get_unused_localhost_port()


@pytest.fixture
def cli_master_publish_port():
    '''
    Returns an unused localhost port for the master publish interface
    '''
    return get_unused_localhost_port()


@pytest.fixture
def cli_master_return_port():
    '''
    Returns an unused localhost port for the master return interface
    '''
    return get_unused_localhost_port()


@pytest.fixture(scope='session')
def session_master_publish_port():
    '''
    Returns an unused localhost port for the master publish interface
    '''
    return get_unused_localhost_port()


@pytest.fixture(scope='session')
def session_master_return_port():
    '''
    Returns an unused localhost port for the master return interface
    '''
    return get_unused_localhost_port()


@pytest.fixture(scope='session')
def session_cli_master_publish_port():
    '''
    Returns an unused localhost port for the master publish interface
    '''
    return get_unused_localhost_port()


@pytest.fixture(scope='session')
def session_cli_master_return_port():
    '''
    Returns an unused localhost port for the master return interface
    '''
    return get_unused_localhost_port()


@pytest.fixture
def master_engine_port():
    return get_unused_localhost_port()


@pytest.fixture
def minion_engine_port():
    return get_unused_localhost_port()


@pytest.fixture(scope='session')
def session_master_engine_port():
    return get_unused_localhost_port()


@pytest.fixture(scope='session')
def session_minion_engine_port():
    return get_unused_localhost_port()


@pytest.fixture
def cli_master_engine_port():
    return get_unused_localhost_port()


@pytest.fixture
def cli_minion_engine_port():
    return get_unused_localhost_port()


@pytest.fixture(scope='session')
def session_cli_master_engine_port():
    return get_unused_localhost_port()


@pytest.fixture(scope='session')
def session_cli_minion_engine_port():
    return get_unused_localhost_port()
