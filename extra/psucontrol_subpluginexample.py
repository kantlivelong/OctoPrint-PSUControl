# coding=utf-8
from __future__ import absolute_import

__author__ = "Shawn Bruce <kantlivelong@gmail.com>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2021 Shawn Bruce - Released under terms of the AGPLv3 License"

import octoprint.plugin

class PSUControl_SubPluginExample(octoprint.plugin.StartupPlugin):

    def __init__(self):
        self.status = False


    def on_startup(self, host, port):
        psucontrol_helpers = self._plugin_manager.get_helpers("psucontrol")
        if 'register_plugin' not in psucontrol_helpers.keys():
            self._logger.warning("The version of PSUControl that is installed does not support plugin registration.")
            return

        self._logger.debug("Registering plugin with PSUControl")
        psucontrol_helpers['register_plugin'](self)


    def turn_psu_on(self):
        self._logger.info("ON")
        self.status = True


    def turn_psu_off(self):
        self._logger.info("OFF")
        self.status = False


    def get_psu_state(self):
        return self.status


__plugin_name__ = "PSU Control - Sub Plugin Example"
__plugin_pythoncompat__ = ">=2.7,<4"

def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = PSUControl_SubPluginExample()
