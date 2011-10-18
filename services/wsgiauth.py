# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is Sync Server
#
# The Initial Developer of the Original Code is the Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2010
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Tarek Ziade (tarek@mozilla.com)
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****
"""
Authentication class.
"""
import binascii
import base64

from webob.exc import HTTPUnauthorized, HTTPBadRequest
from cef import log_cef, AUTH_FAILURE

from services.pluginreg import load_and_configure
from services.user import User, extract_username


class Authentication(object):
    """Authentication tool. Defines the authentication strategy.

    Each services application can use a subclass of "Authentication" to define
    its own authentication strategy.  The class must provide two methods:

        * check(request, match):  check whether auth is required, extract and
                                  verify credentials, and possibly raise an
                                  error if auth fails.

        * acknowledge(request, response):  add headers to the response to
                                           acknowledge successful auth.

    The base class implementation uses HTTP-Basic-Auth to authenticate
    users.  New applications should consider using the "WhoAuthentication"
    class from services.whoauth, which uses repoze.who to provide a pluggable
    authentication stack.
    """
    def __init__(self, config):
        self.config = config
        self.backend = load_and_configure(self.config, 'auth')

    def check(self, request, match):
        """Checks if the current request/match can be viewed.

        This function can raise HTTPUnauthorized, or redirect to a
        login page.
        """
        if match.get('auth') != 'True':
            return

        user_id = self.authenticate_user(request, self.config,
                                         match.get('username'))
        if user_id is None:
            headers = [('WWW-Authenticate', 'Basic realm="Sync"'),
                       ('Content-Type', 'text/plain')]
            raise HTTPUnauthorized(headerlist=headers)

        match['user_id'] = user_id

    def acknowledge(self, request, response):
        """Acknowledges successful auth back to the user.

        This method might send a HTTP Authentication-Info header or set a
        cookie allowing the client to remember its login session.
        """
        pass

    def authenticate_user(self, request, config, username=None):
        """Authenticates a user and returns his id.

        "request" is the request received.
        The function makes sure that the user name found in the headers
        is compatible with the username if provided.

        It returns the user id from the database, if the password is the right
        one.
        """
        environ = request.environ

        if 'REMOTE_USER' in environ:
            # already authenticated
            return environ['REMOTE_USER']

        auth = environ.get('HTTP_AUTHORIZATION')
        if auth is not None:
            # for now, only supporting basic authentication
            # let's decipher the base64 encoded value
            if not auth.startswith('Basic '):
                raise HTTPUnauthorized('Invalid token')

            auth = auth[len('Basic '):].strip()
            try:
                # Split in such a way as to preserve
                # passwords that contain ':'.
                user_name, password = base64.decodestring(auth).split(':', 1)
            except (binascii.Error, ValueError):
                raise HTTPUnauthorized('Invalid token')

            # let's reject the call if the url is not owned by the user
            if (username is not None and user_name != username):
                log_cef('Username Does Not Match URL', 7, environ, config,
                        user_name, AUTH_FAILURE)
                raise HTTPUnauthorized()

            # if this is an email, hash it. Save the original for logging and
            #  debugging.
            remote_user_original = user_name
            try:
                user_name = extract_username(user_name)
            except UnicodeError:
                raise HTTPBadRequest('Invalid characters specified in ' +
                                     'username', {}, 'Username must be BIDI ' +
                                     'compliant UTF-8')

            # let's try an authentication
            # the authenticate_user API takes a unicode UTF-8 for the password
            try:
                password = password.decode('utf8')
            except UnicodeDecodeError:
                raise HTTPUnauthorized()

            #first we need to figure out if this is old-style or new-style auth
            if hasattr(self.backend, 'generate_reset_code'):

            # XXX to be removed once we get the proper fix see bug #662859
                if (hasattr(self.backend, 'check_node')
                    and self.backend.check_node):
                    user_id = self.backend.authenticate_user(user_name,
                                            password, environ.get('HTTP_HOST'))
                else:
                    user_id = self.backend.authenticate_user(user_name,
                                                             password)
                request.user = User(user_name, user_id)
            else:
                user = User(user_name)
                user_id = self.backend.authenticate_user(user, password,
                                                         ['syncNode'])
                if (self.config.get('auth.check_node')
                    and user.get('syncNode') != environ.get('HTTP_HOST')):
                    user_id = None
                    user = None

                request.user = user

            if user_id is None:
                err_user = user_name
                if remote_user_original is not None and \
                    user_name != remote_user_original:
                        err_user += ' (%s)' % (remote_user_original)
                log_cef('User Authentication Failed', 5, environ, config,
                        err_user, AUTH_FAILURE)
                raise HTTPUnauthorized()

            # we're all clear ! setting up REMOTE_USER
            request.remote_user = environ['REMOTE_USER'] = user_name

            # we also want to keep the password in clear text to reuse it
            # and remove it from the environ
            request.user_password = password
            request._authorization = environ['HTTP_AUTHORIZATION']

            del environ['HTTP_AUTHORIZATION']
            return user_id
