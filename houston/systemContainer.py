try:
    import docker
except ImportError:
    pass

import os
import houston
import site
import sys
import requests
import mission


# Find the location of Houston on disk
# PATH_TO_SITE_PKGS = site.getsitepackages()[0]
PATH_TO_HOUSTON_EGG = os.path.dirname(os.path.dirname(houston.__file__))
HOUSTON_SCRIPT_PATHS = [ # TODO: use `which` command
    '/usr/local/bin/houstonserver'
]


class SystemContainer(object):
    """
    System proxies are used to

    - ensures clean-up
    """
    def __init__(self, iden, image, port, verbose=False):
        """
        Constructs a new SystemContainer

        :param  iden:       the identifier of the system to which this container\
                            belongs
        :param  image:      the name of the Docker image to use for this container
        :param  port:       the number of the port that the Houston server should\
                            run on
        :param  verbose:    a flag indicating whether the output from this \
                            container should be dumped before its destruction.
        """
        assert (isinstance(port, int) and not port is None)
        assert (port >= 1024 and port < 65535)

        self.__verbose = verbose
        self.__systemIdentifier = iden
        self.__port = port
        self.__image = image
        self.__prepare()


    def __prepare(self):
        command = 'houstonserver {}'.format(self.__port)
        ports = {self.__port: self.__port}

        # prepare Houston library and scripts for auto-mounting
        volumes = {
            PATH_TO_HOUSTON_EGG: {'bind': PATH_TO_HOUSTON_EGG, 'mode': 'ro'}
        }
        for path in HOUSTON_SCRIPT_PATHS:
            volumes[path] = {'bind': path, 'mode': 'ro'}

        client = docker.from_env()
        self.__container = client.containers.run(self.__image,
                                                 command,
                                                 network_mode='bridge',
                                                 ports=ports,
                                                 volumes=volumes,
                                                 detach=True)

         # blocks until server is running
        for line in self.__container.logs(stream=True):
            line = line.strip()
            if line.startswith('* Running on http://'):
                break


    def reset(self):
        self.destroy()
        self.__prepare()


    def ready(self):
        """
        Returns true if the server running inside this system container is
        ready to accept requests.
        """
        return True


    def systemIdentifier(self):
        """
        Returns the identifier of the system to which this container belongs.
        """
        return self.__systemIdentifier


    def port(self):
        """
        Returns the port in use by this container.
        """
        return self.__port


    def container(self):
        """
        Returns a handle for the associated Docker container
        """
        return self.__container


    def execute(self, msn):
        """
        Executes a given mission inside this container and returns the result.
        """
        assert(isinstance(msn, mission.Mission))
        assert(not msn is None)
        jsn = msn.toJSON()
        jsn = {'system': self.systemIdentifier(), 'mission': jsn}
        url = 'http://127.0.0.1:{}/executeMission'.format(self.__port)
        r = requests.post(url, json=jsn)

        outcome = mission.MissionOutcome.fromJSON(r.json())
        if self.__verbose:
            print(outcome.toJSON())

        # TODO: add timeout
        # TODO: handle unexpected responses
        return outcome


    def destroy(self):
        """
        Destroys the attached Docker container.
        """
        if self.__verbose:
            print(self.__container.logs(stdout=True, stderr=True))

        self.__container.kill()
        self.__container.remove(force=True)
        self.__container = None
