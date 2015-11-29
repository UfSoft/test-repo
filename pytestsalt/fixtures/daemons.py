# -*- coding: utf-8 -*-
'''
    :codeauthor: :email:`Pedro Algarvio (pedro@algarvio.me)`
    :copyright: © 2015 by the SaltStack Team, see AUTHORS for more details.
    :license: Apache 2.0, see LICENSE for more details.


    pytestsalt.fixtures.daemons
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Salt daemons fixtures
'''
# pylint: disable=redefined-outer-name

# Import python libs
from __future__ import absolute_import, print_function
import os
import sys
import time
import signal
import socket
import logging
import functools
import subprocess
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor


# Import salt libs
import salt.master
import salt.minion
import salt.log.setup
import salt.utils.timed_subprocess as timed_subprocess
from salt.utils.process import MultiprocessingProcess
from salt.exceptions import SaltDaemonNotRunning, TimedProcTimeoutError

# Import 3rd-party libs
import pytest
import tornado

log = logging.getLogger(__name__)

HANDLED_LEVELS = {
    2: 'warning',       # logging.WARN,    # -v
    3: 'info',          # logging.INFO,    # -vv
    4: 'debug',         # logging.DEBUG,   # -vvv
    5: 'trace',         # logging.TRACE,   # -vvvv
    6: 'garbage'        # logging.GARBAGE  # -vvvvv
}


def get_log_level_name(verbosity):
    '''
    Return the CLI logging level name based on pytest verbosity
    '''
    return HANDLED_LEVELS.get(verbosity,
                              HANDLED_LEVELS.get(verbosity > 6 and 6 or 2))


@pytest.yield_fixture(scope='session')
def mp_logging_setup():
    '''
    Returns the salt process manager from _process_manager.

    We need these two functions to properly shutdown the process manager
    '''
    log.warning('starting multiprocessing logging')
    salt.log.setup.setup_multiprocessing_logging_listener()
    log.warning('multiprocessing logging started')
    yield
    log.warning('stopping multiprocessing logging')
    salt.log.setup.shutdown_multiprocessing_logging()
    salt.log.setup.shutdown_multiprocessing_logging_listener()
    log.warning('multiprocessing logging stopped')


@pytest.yield_fixture
def salt_master(mp_logging_setup, master_config, minion_config):
    '''
    Returns a running salt-master
    '''
    log.warning('Starting salt-master')
    master_process = SaltMaster(master_config, minion_config)
    master_process.start()
    if master_process.is_alive():
        try:
            retcode = master_process.wait_until_running(timeout=15)
            if not retcode:
                os.kill(master_process.pid, signal.SIGTERM)
                master_process.join()
                master_process.terminate()
                pytest.skip('The pytest function scoped salt-master has failed to start')
        except SaltDaemonNotRunning as exc:
            os.kill(master_process.pid, signal.SIGTERM)
            master_process.join()
            master_process.terminate()
            pytest.skip(str(exc))
        log.warning('The pytest function scoped salt-master is running and accepting connections')
        yield master_process
    else:
        master_process.join()
        master_process.terminate()
        pytest.skip('The pytest function scoped salt-master has failed to start')
    log.warning('Stopping function scoped salt-master')
    os.kill(master_process.pid, signal.SIGTERM)
    master_process.join()
    master_process.terminate()
    log.warning('Function scoped salt-master stopped')


@pytest.yield_fixture
def salt_minion(mp_logging_setup, minion_config, salt_master):
    '''
    Returns a running salt-minion
    '''
    log.warning('Starting salt-minion')
    minion_process = SaltMinion(minion_config)
    minion_process.start()
    if minion_process.is_alive():
        try:
            retcode = minion_process.wait_until_running(timeout=15)
            if not retcode:
                os.kill(minion_process.pid, signal.SIGTERM)
                minion_process.join()
                minion_process.terminate()
                pytest.skip('The pytest function scoped salt-minion has failed to start')
        except SaltDaemonNotRunning as exc:
            os.kill(minion_process.pid, signal.SIGTERM)
            minion_process.join()
            minion_process.terminate()
            pytest.skip(str(exc))
        log.warning('The pytest function scoped salt-minion is running and accepting connections')
        yield minion_process
    else:
        minion_process.join()
        minion_process.terminate()
        pytest.skip('The pytest function scoped salt-minion has failed to start')
    log.warning('Stopping function scoped salt-minion')
    os.kill(minion_process.pid, signal.SIGTERM)
    minion_process.join()
    minion_process.terminate()
    log.warning('Function scoped salt-minion stopped')


@pytest.yield_fixture
def cli_salt_master(request,
                    mp_logging_setup,
                    cli_conf_dir,
                    cli_master_config,
                    cli_minion_config,
                    io_loop):
    '''
    Returns a running salt-master
    '''
    log.warning('Starting CLI salt-master')
    master_process = SaltCliMaster(cli_master_config,
                                   cli_conf_dir.strpath,
                                   request.config.getoption('--cli-bin-dir'),
                                   request.config.getoption('-v'),
                                   io_loop)
    master_process.start()
    if master_process.is_alive():
        try:
            retcode = master_process.wait_until_running(timeout=10)
            if not retcode:
                os.kill(master_process.pid, signal.SIGTERM)
                master_process.join()
                master_process.terminate()
                pytest.skip('The pytest salt-master has failed to start')
        except TimedProcTimeoutError as exc:
            os.kill(master_process.pid, signal.SIGTERM)
            master_process.join()
            master_process.terminate()
            pytest.skip(str(exc))
        log.warning('The pytest CLI salt-master is running and accepting connections')
        yield master_process
    else:
        #os.kill(master_process.pid, signal.SIGTERM)
        master_process.join()
        master_process.terminate()
        pytest.skip('The pytest salt-master has failed to start')
    log.warning('Stopping CLI salt-master')
    try:
        os.kill(master_process.pid, signal.SIGTERM)
    except OSError:
        pass
    master_process.join()
    master_process.terminate()
    log.warning('CLI salt-master stopped')


@pytest.yield_fixture
def cli_salt_minion(request,
                    mp_logging_setup,
                    cli_conf_dir,
                    cli_salt_master,
                    cli_minion_config,
                    io_loop):
    '''
    Returns a running salt-minion
    '''
    log.warning('Starting CLI salt-minion')
    minion_process = SaltCliMinion(cli_minion_config,
                                   cli_conf_dir.strpath,
                                   request.config.getoption('--cli-bin-dir'),
                                   request.config.getoption('-v'),
                                   io_loop)
    minion_process.start()
    # Allow the subprocess to start
    time.sleep(0.5)
    if minion_process.is_alive():
        try:
            retcode = minion_process.wait_until_running(timeout=5)
            if not retcode:
                os.kill(minion_process.pid, signal.SIGTERM)
                minion_process.join()
                minion_process.terminate()
                pytest.skip('The pytest salt-minion has failed to start')
        except TimedProcTimeoutError as exc:
            os.kill(minion_process.pid, signal.SIGTERM)
            minion_process.join()
            minion_process.terminate()
            pytest.skip(str(exc))
        log.warning('The pytest CLI salt-minion is running and accepting commands')
        yield minion_process
    else:
        #os.kill(minion_process.pid, signal.SIGTERM)
        minion_process.join()
        minion_process.terminate()
        pytest.skip('The pytest salt-minion has failed to start')
    log.warning('Stopping CLI salt-minion')
    os.kill(minion_process.pid, signal.SIGTERM)
    minion_process.join()
    minion_process.terminate()
    log.warning('CLI salt-minion stopped')


@pytest.yield_fixture(scope='session')
def session_salt_master(mp_logging_setup,
                        session_master_config,
                        session_minion_config):
    '''
    Returns a running salt-master
    '''
    log.warning('Starting salt-master')
    master_process = SaltMaster(session_master_config, session_minion_config)
    master_process.start()
    if master_process.is_alive():
        try:
            retcode = master_process.wait_until_running(timeout=15)
            if not retcode:
                os.kill(master_process.pid, signal.SIGTERM)
                master_process.join()
                master_process.terminate()
                pytest.skip('The pytest session scoped salt-master has failed to start')
        except SaltDaemonNotRunning as exc:
            os.kill(master_process.pid, signal.SIGTERM)
            master_process.join()
            master_process.terminate()
            pytest.skip(str(exc))
        log.warning('The pytest session scoped salt-master is running and accepting connections')
        yield master_process
    else:
        master_process.join()
        master_process.terminate()
        pytest.skip('The pytest session scoped salt-master has failed to start')
    log.warning('Stopping session scoped salt-master')
    os.kill(master_process.pid, signal.SIGTERM)
    master_process.join()
    master_process.terminate()
    log.warning('Session scoped salt-master stopped')


@pytest.yield_fixture(scope='session')
def session_salt_minion(mp_logging_setup, session_minion_config, session_salt_master):
    '''
    Returns a running salt-minion
    '''
    log.warning('Starting pytest session scoped salt-minion')
    minion_process = SaltMinion(session_minion_config)
    minion_process.start()
    if minion_process.is_alive():
        try:
            retcode = minion_process.wait_until_running(timeout=15)
            if not retcode:
                os.kill(minion_process.pid, signal.SIGTERM)
                minion_process.join()
                minion_process.terminate()
                pytest.skip('The pytest session scoped salt-minion has failed to start')
        except SaltDaemonNotRunning as exc:
            os.kill(minion_process.pid, signal.SIGTERM)
            minion_process.join()
            minion_process.terminate()
            pytest.skip(str(exc))
        log.warning('The pytest session scoped salt-minion is running and accepting connections')
        yield minion_process
    else:
        minion_process.join()
        minion_process.terminate()
        pytest.skip('The pytest session scoped salt-minion has failed to start')
    log.warning('Stopping session scoped salt-minion')
    os.kill(minion_process.pid, signal.SIGTERM)
    minion_process.join()
    minion_process.terminate()
    log.warning('Session scoped salt-minion stopped')


@pytest.yield_fixture(scope='session')
def session_cli_salt_master(request,
                            mp_logging_setup,
                            session_cli_conf_dir,
                            session_cli_master_config,
                            session_cli_minion_config):
    '''
    Returns a running salt-master
    '''
    log.warning('Starting CLI salt-master')
    master_process = SaltCliMaster(session_cli_master_config,
                                   session_cli_conf_dir.strpath,
                                   request.config.getoption('--cli-bin-dir'),
                                   verbosity=request.config.getoption('-v'))
    master_process.start()
    if master_process.is_alive():
        try:
            retcode = master_process.wait_until_running(timeout=15)
            if not retcode:
                os.kill(master_process.pid, signal.SIGTERM)
                master_process.join()
                master_process.terminate()
                pytest.skip('The pytest salt-master has failed to start')
        except TimedProcTimeoutError as exc:
            #os.kill(master_process.pid, signal.SIGTERM)
            master_process.join()
            master_process.terminate()
            pytest.skip(str(exc))
        log.warning('The pytest CLI salt-master is running and accepting connections')
        yield master_process
    else:
        #os.kill(master_process.pid, signal.SIGTERM)
        master_process.join()
        master_process.terminate()
        pytest.skip('The pytest salt-master has failed to start')
    log.warning('Stopping CLI salt-master')
    os.kill(master_process.pid, signal.SIGTERM)
    master_process.join()
    master_process.terminate()
    log.warning('CLI salt-master stopped')


@pytest.yield_fixture(scope='session')
def session_cli_salt_minion(request,
                            mp_logging_setup,
                            session_cli_conf_dir,
                            session_cli_salt_master,
                            session_cli_minion_config):
    '''
    Returns a running salt-minion
    '''
    log.warning('Starting CLI salt-master')
    minion_process = SaltCliMinion(session_cli_minion_config,
                                   session_cli_conf_dir.strpath,
                                   request.config.getoption('--cli-bin-dir'),
                                   verbosity=request.config.getoption('-v'))
    minion_process.start()
    # Allow the subprocess to start
    time.sleep(0.5)
    if minion_process.is_alive():
        try:
            retcode = minion_process.wait_until_running(timeout=10)
            if not retcode:
                os.kill(minion_process.pid, signal.SIGTERM)
                minion_process.join()
                minion_process.terminate()
                pytest.skip('The pytest salt-minion has failed to start')
        except TimedProcTimeoutError as exc:
            os.kill(minion_process.pid, signal.SIGTERM)
            minion_process.join()
            minion_process.terminate()
            pytest.skip(str(exc))
        log.warning('The pytest CLI salt-minion is running and accepting commands')
        yield minion_process
    else:
        os.kill(minion_process.pid, signal.SIGTERM)
        minion_process.join()
        minion_process.terminate()
        pytest.skip('The pytest salt-minion has failed to start')
    log.warning('Stopping CLI salt-minion')
    os.kill(minion_process.pid, signal.SIGTERM)
    minion_process.join()
    minion_process.terminate()
    log.warning('CLI salt-minion stopped')


class SaltMinion(multiprocessing.Process):
    '''
    Multiprocessing process for running a salt-minion
    '''
    def __init__(self, minion_opts):
        super(SaltMinion, self).__init__()
        self.minion = salt.minion.Minion(minion_opts)

    def wait_until_running(self, timeout=None):
        '''
        Block waiting until we can confirm that the minion is up and running
        and connected to a master
        '''
        self.minion.sync_connect_master(timeout=timeout)
        # Let's issue a test.ping to make sure the minion's transport stream
        # attribute is set, which will avoid a hanging test session termination
        # because of the following exception:
        #   Exception AttributeError: "'NoneType' object has no attribute 'zmqstream'" in
        #       <bound method Minion.__del__ of <salt.minion.Minion object at 0x7f2c41bf6390>> ignored
        return self.minion.functions.test.ping()

    def run(self):
        self.minion.tune_in()


class SaltMaster(SaltMinion):
    '''
    Multiprocessing process for running a salt-master
    '''
    def __init__(self, master_opts, minion_opts):
        super(SaltMaster, self).__init__(minion_opts)
        self.master = salt.master.Master(master_opts)

    def run(self):
        self.master.start()


class SaltCliScriptBase(MultiprocessingProcess):

    cli_script_name = None

    def __init__(self, config, config_dir, bin_dir_path, verbosity, io_loop=None):
        super(SaltCliScriptBase, self).__init__(log_queue=salt.log.setup.get_multiprocessing_logging_queue())
        self.config = config
        self.config_dir = config_dir
        self.bin_dir_path = bin_dir_path
        self.verbosity = verbosity
        if io_loop is not None:
            self._io_loop = io_loop

    def __setstate__(self, state):
        MultiprocessingProcess.__init__(self, log_queue=state['log_queue'])
        self.config = state['config']
        self.config_dir = state['config_dir']
        self.bin_dir_path = state['bin_dir_path']
        self.verbosity = state['verbosity']

    def __getstate__(self):
        return {'config': self.config,
                'config_dir': self.config_dir,
                'bin_dir_path': self.bin_dir_path,
                'verbosity': self.verbosity}

    def get_script_path(self, scrip_name):
        return os.path.join(self.bin_dir_path, scrip_name)

    def _on_signal(self, pid, signum, sigframe):
        log.warning('received signal: %s', signum)
        # escalate the signal
        os.kill(pid, signum)

    @property
    def io_loop(self):
        if not getattr(self, '_io_loop', None) is None:
            log.warning('\n\nCreating IOLoop!')
            self._io_loop = tornado.ioloop.IOLoop.instance()
            self._io_loop.make_current()
            self._io_loop.start()
        return self._io_loop

    @property
    def executor(self):
        if not hasattr(self, '_executor'):
            log.warning('\n\nCreating ThreadPoolExecutor!')
            self._executor = ThreadPoolExecutor(max_workers=4)
            #self._executor = ProcessPoolExecutor(max_workers=4)
        return self._executor

    def run(self):
        import signal
        log.warning('Starting %s CLI DAEMON', self.__class__.__name__)
        proc_args = [
            self.get_script_path(self.cli_script_name),
            '-c',
            self.config_dir,
            '-l', get_log_level_name(self.verbosity)
            #'-l', 'debug'
        ]
        log.warn('Running \'%s\' from %s...', ' '.join(proc_args), self.__class__.__name__)
        proc = subprocess.Popen(
            proc_args,
        )
        signal.signal(signal.SIGINT, functools.partial(self._on_signal, proc.pid))
        signal.signal(signal.SIGTERM, functools.partial(self._on_signal, proc.pid))
        proc.communicate()


class SaltCliMinion(SaltCliScriptBase):

    cli_script_name = 'salt-minion'

    def wait_until_running(self, timeout=None):
        if timeout is not None:
            until = time.time() + timeout
        check_ports = set([self.config['pytest_port']])
        connectable = False
        while True:
            if not check_ports:
                connectable = True
                break
            if time.time() >= until:
                break
            for port in set(check_ports):
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                conn = sock.connect_ex(('localhost', port))
                if conn == 0:
                    check_ports.remove(port)
                    sock.shutdown(socket.SHUT_RDWR)
                    sock.close()
                del sock
            time.sleep(0.125)
        return connectable

    #@tornado.gen.coroutine
    def ping_master(self, timeout=5):
        ##return self.io_loop.run_sync(self._salt_call('test.ping', timeout=timeout))
        #result = yield self._salt_call('test.ping', timeout=timeout)
        #return result
        future = self._salt_call('test.ping', timeout=timeout)
        #while future.running():
        #    time.sleep(0.25)
            #yield tornado.gen.sleep(0.5)
        return future.result()

    #@tornado.gen.coroutine
    def sync(self, timeout=5):
        ##return self.io_loop.run_sync(self._salt_call('saltutil.sync_all', timeout=timeout))
        #result = yield self._salt_call('saltutil.sync_all', timeout=timeout)
        #return result
        future = self._salt_call('saltutil.sync_all', timeout=timeout)
        #while future.running():
        #    time.sleep(0.25)
        #    #yield tornado.gen.sleep(0.5)
        return future.result()

    def _salt_call(self, *args, **kwargs):
        #@tornado.concurrent.run_on_executor(executor
        def _executor_run(*args, **kwargs):
            timeout = kwargs.pop('timeout', 5)
            proc_args = [
                self.get_script_path('salt-call'),
                '-c',
                self.config_dir,
                '--retcode-passthrough',
                '-l', get_log_level_name(self.verbosity),
                #'-l', 'trace',
                #'-l', 'debug',
                #'--out', 'quiet',
            ] + list(args)
            log.warn('Running \'%s\' from %s...', ' '.join(proc_args), self.__class__.__name__)
            print('Running \'{}\' from {}...'.format(' '.join(proc_args), self.__class__.__name__))
            proc = timed_subprocess.TimedProc(
                proc_args,
                with_communicate=True
            )
            try:
                print('Communicate:', proc.wait(timeout))
                log.warning('salt-call finished. retcode: %s', proc.process.returncode)
                #print('Communicate:', proc.)
                return proc.process.returncode == 0
            except TimedProcTimeoutError:
                log.warning('\n\nTimed out!!!   %s', proc.process.communicate())
                return False
        return self.executor.submit(_executor_run, *args, **kwargs)
        return tornado.gen.maybe_future(_executor_run(*args, **kwargs))


class SaltCliMaster(SaltCliMinion):

    cli_script_name = 'salt-master'

    def wait_until_running(self, timeout=None):
        if timeout is not None:
            until = time.time() + timeout
        check_ports = set([self.config['ret_port'],
                           self.config['publish_port'],
                           self.config['pytest_port']])
        connectable = False
        while True:
            if not check_ports:
                connectable = True
                break
            if time.time() >= until:
                break
            for port in set(check_ports):
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                conn = sock.connect_ex(('localhost', port))
                if conn == 0:
                    check_ports.remove(port)
                    sock.shutdown(socket.SHUT_RDWR)
                    sock.close()
                del sock
            time.sleep(0.125)
        return connectable


def pytest_addoption(parser):
    '''
    Add pytest salt plugin daemons related options
    '''
    saltparser = parser.getgroup('Salt Plugin Options')
    saltparser.addoption(
        '--cli-bin-dir',
        default=os.path.dirname(sys.executable),
        help=('Path to the bin directory where the salt daemon\'s scripts can be '
              'found. Defaults to the directory name of the python executable '
              'running py.test')
    )
