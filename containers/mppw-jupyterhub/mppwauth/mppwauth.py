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