import os
import pwd
import subprocess

import requests
import mppw_clients
from jupyterhub.auth import LocalAuthenticator

class MppwAuthenticator(LocalAuthenticator):

    #passwords = {"some_user": "password"}

    def get_mppw_url(self):
        return os.environ.get("AUTHENTICATOR_MPPW_URL", "http://mppw:8000/api")

    async def authenticate(self, handler, data):
        
        api = mppw_clients.MppwApiClient(self.get_mppw_url(), https_verify=False, require_login=False)
        try:
            api.login(data['username'], data['password'])
            return data['username']
        except requests.exceptions.HTTPError as ex:
            self.log.error(f"Could not authenticate with user {data['username']} at {self.get_mppw_url()}: {ex}")
            return None

    def user_home_dir_exists(self, username: str) -> bool:

        """
        Verify user home directory exists
        """

        try:
            user = pwd.getpwnam(username)
            home_dir = user.pw_dir
            return os.path.isdir(home_dir)
        except KeyError:
            return False

    def add_user_home_dir(self, username: str) -> None:
        
        """
        Creates user home directory
        """
        
        cmd = ['mkhomedir_helper'] + [username]
        self.log.info("Creating '{}' user home directory using command '{}'".format(
            username, ' '.join(cmd)))
        proc = subprocess.Popen(cmd,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                universal_newlines=True)
        out, err = proc.communicate()
        if proc.returncode:
            raise RuntimeError("Failed to create '{}' user home directory: {}".format(
                username, err))