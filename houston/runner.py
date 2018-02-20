import threading
import time
import signal
from houston.util import TimeoutError, printflush


class MissionRunner(threading.Thread):
    """
    Mission runners are used to continually fetch pending tests from an
    associated pool, and to execute those tests.
    """
    def __init__(self, pool):
        super(MissionRunner, self).__init__()
        self.daemon = True
        self.__pool = pool
        self.__container = pool.system.provision()

    def run(self):
        """
        Continues to process jobs.
        """
        while True:
            m = self.__pool.fetch()
            if m is None:
                return

            outcome = self.__container.execute(m)
            self.__pool.report(m, outcome)

    def shutdown(self):
        if self.__container is not None:
            self.__container.destroy()
            self.__container = None


class MissionRunnerPool(object):
    """
    Mission runner pools are used to distribute the execution of a stream
    of missions across a given number of workers, each running on a separate
    thread.
    """
    def __init__(self, system, size, source, callback):
        assert isinstance(size, int)
        assert callable(callback)
        assert size > 0

        # if a list is provided, use an iterator for that list
        if isinstance(source, list):
            source = source.__iter__()

        self.__system = system
        self.__source = source
        self.__callback = callback
        self._lock = threading.Lock()

        # provision desired number of runners
        self.__runners = [MissionRunner(self) for _ in range(size)]

    def run(self):
        """

        """
        try:
            for runner in self.__runners:
                runner.start()

            # soft block until all runners have finished
            # (unlike join, we allow exceptions to be thrown to the parent
            #  thread)
            while True:
                if not any(runner.is_alive() for runner in self.__runners):
                    break
                time.sleep(0.1)

        finally:
            self.shutdown()

    def shutdown(self):
        """
        Kills all runners that belong to this pool.
        """
        if self.__runners == []:
            return

        for runner in self.__runners:
            if runner is not None:
                runner.shutdown()
        self.__runners = []

    @property
    def system(self):
        """
        The system under test.
        """
        return self.__system

    @property
    def size(self):
        """
        The number of independent threads being used by the pool to run
        tests.
        """
        return self.__runners.length()

    def report(self, mission, outcome):
        """
        Used to report the outcome of a mission.

        WARNING: It is the responsibility of the callback to guarantee
            thread safety (if necessary).
        """
        self.__callback(mission, outcome)

    def fetch(self):
        """
        Returns the next mission from the (lazily-generated) queue, or None if
        there are no missions left to run.

        This method is considered to be thread safe (no concurrent reads from
        the source of the pool are allowed).
        """
        # acquire fetch lock
        self._lock.acquire()
        try:
            return self.__source.next()

        except StopIteration:
            return None

        finally:
            self._lock.release()
