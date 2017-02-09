# coding=utf-8
from __future__ import absolute_import

__author__ = "Shawn Bruce <kantlivelong@gmail.com>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2017 Shawn Bruce - Released under terms of the AGPLv3 License"

import octoprint.plugin
from octoprint.server import user_permission
from octoprint.util import RepeatedTimer
import RPi.GPIO as GPIO
import time
import threading
import os

class PSUControl(octoprint.plugin.StartupPlugin,
                   octoprint.plugin.TemplatePlugin,
                   octoprint.plugin.AssetPlugin,
                   octoprint.plugin.SettingsPlugin,
                   octoprint.plugin.SimpleApiPlugin):

    def __init__(self):
        self.switchingMethod = ''
        self.onoffGPIOPin = 0
        self.invertonoffGPIOPin = False
        self.onGCodeCommand = ''
        self.offGCodeCommand = ''
	self.onSysCommand = ''
	self.offSysCommand = ''
        self.autoOn = False
        self.autoOnCommands = ''
        self.autoOnCommandsArray = []
        self.powerOffWhenIdle = False
        self.idleTimeout = 0
        self.idleIgnoreCommands = ''
        self.idleIgnoreCommandsArray = []
        self.idleTimeoutWaitTemp = 0
        self.enableSensing = False
        self.senseGPIOPin = 0
        self.isPSUOn = False
        self._noSensing_isPSUOn = False
        self._checkPSUTimer = None
        self._idleTimer = None
        self._waitForHeaters = False
        self._skipIdleTimer = False

    def initialize(self):
        self.switchingMethod = self._settings.get(["switchingMethod"])
        self._logger.debug("switchingMethod: %s" % self.switchingMethod)

        self.onoffGPIOPin = self._settings.get_int(["onoffGPIOPin"])
        self._logger.debug("onoffGPIOPin: %s" % self.onoffGPIOPin)

        self.invertonoffGPIOPin = self._settings.get_boolean(["invertonoffGPIOPin"])
        self._logger.debug("invertonoffGPIOPin: %s" % self.invertonoffGPIOPin)

        self.onGCodeCommand = self._settings.get(["onGCodeCommand"])
        self._logger.debug("onGCodeCommand: %s" % self.onGCodeCommand)

        self.offGCodeCommand = self._settings.get(["offGCodeCommand"])
        self._logger.debug("offGCodeCommand: %s" % self.offGCodeCommand)

        self.onSysCommand = self._settings.get(["onSysCommand"])
        self._logger.debug("onSysCommand: %s" % self.onSysCommand)

        self.offSysCommand = self._settings.get(["offSysCommand"])
        self._logger.debug("offSysCommand: %s" % self.offSysCommand)
	
        self.enableSensing = self._settings.get_boolean(["enableSensing"])
        self._logger.debug("enableSensing: %s" % self.enableSensing)

        self.senseGPIOPin = self._settings.get_int(["senseGPIOPin"])
        self._logger.debug("senseGPIOPin: %s" % self.senseGPIOPin)

        self.autoOn = self._settings.get_boolean(["autoOn"])
        self._logger.debug("autoOn: %s" % self.autoOn)

        self.autoOnCommands = self._settings.get(["autoOnCommands"])
        self.autoOnCommandsArray = self.autoOnCommands.split(',')
        self._logger.debug("autoOnCommands: %s" % self.autoOnCommands)

        self.powerOffWhenIdle = self._settings.get_boolean(["powerOffWhenIdle"])
        self._logger.debug("powerOffWhenIdle: %s" % self.powerOffWhenIdle)

        self.idleTimeout = self._settings.get_int(["idleTimeout"])
        self._logger.debug("idleTimeout: %s" % self.idleTimeout)

        self.idleIgnoreCommands = self._settings.get(["idleIgnoreCommands"])
        self.idleIgnoreCommandsArray = self.idleIgnoreCommands.split(',')
        self._logger.debug("idleIgnoreCommands: %s" % self.idleIgnoreCommands)

        self.idleTimeoutWaitTemp = self._settings.get_int(["idleTimeoutWaitTemp"])
        self._logger.debug("idleTimeoutWaitTemp: %s" % self.idleTimeoutWaitTemp)

        self._configure_gpio()

        self._checkPSUTimer = RepeatedTimer(5.0, self.check_psu_state, None, None, True)
        self._checkPSUTimer.start()

        self._start_idle_timer()

    def _configure_gpio(self):
        self._logger.info("Running RPi.GPIO version %s" % GPIO.VERSION)
        if GPIO.VERSION < "0.6":
            self._logger.error("RPi.GPIO version 0.6.0 or greater required.")
        
        GPIO.setwarnings(False)
        GPIO.cleanup()
        GPIO.setmode(GPIO.BOARD)
        
        if self.enableSensing:
            self._logger.info("Using sensing to determine PSU on/off state.")
            self._logger.info("Configuring GPIO for pin %s" % self.senseGPIOPin)
            try:
                GPIO.setup(self.senseGPIOPin, GPIO.IN)
            except (RuntimeError, ValueError) as e:
                self._logger.error(e)
        
        if self.switchingMethod == 'COMMAND':
            self._logger.info("Using Commands for On/Off")
	elif self.switchingMethod == 'SYSTEM':
	    self._logger.info("Using System Commands for On/Off")
        elif self.switchingMethod == 'GPIO':
            self._logger.info("Using GPIO for On/Off")
            self._logger.info("Configuring GPIO for pin %s" % self.onoffGPIOPin)
            try:
                GPIO.setup(self.onoffGPIOPin, GPIO.OUT)
            except (RuntimeError, ValueError) as e:
                self._logger.error(e)

    def check_psu_state(self):
	old_isPSUOn = self.isPSUOn

        if self.enableSensing:
            self._logger.debug("Polling PSU state...")
            r = 0
            try:
                r = GPIO.input(self.senseGPIOPin)
            except (RuntimeError, ValueError) as e:
                self._logger.error(e)
            self._logger.debug("Result: %s" % r)

            if r==1:
                self.isPSUOn = True
            elif r==0:
                self.isPSUOn = False
        else:
            self.isPSUOn = self._noSensing_isPSUOn
        
        self._logger.debug("isPSUOn: %s" % self.isPSUOn)

        if (old_isPSUOn != self.isPSUOn) and self.isPSUOn:
            self._start_idle_timer()
        elif (old_isPSUOn != self.isPSUOn) and not self.isPSUOn:
            self._stop_idle_timer()

        self._plugin_manager.send_plugin_message(self._identifier, dict(isPSUOn=self.isPSUOn))

    def _start_idle_timer(self):
        self._stop_idle_timer()
        
        if self.powerOffWhenIdle and self.isPSUOn:
            self._idleTimer = threading.Timer(self.idleTimeout * 60, self._idle_poweroff)
            self._idleTimer.start()

    def _stop_idle_timer(self):
        if self._idleTimer:
            self._idleTimer.cancel()
            self._idleTimer = None

    def _idle_poweroff(self):
        if not self.powerOffWhenIdle:
            return
        
        if self._waitForHeaters:
            return
        
        if self._printer.is_printing() or self._printer.is_paused():
            return

        self._logger.info("Idle timeout reached after %s minute(s). Turning heaters off prior to shutting off PSU." % self.idleTimeout)
        if self._wait_for_heaters():
            self._logger.info("Heaters below temperature.")
            self.turn_psu_off()
        else:
            self._logger.info("Aborted PSU shut down due to activity.")

    def _wait_for_heaters(self):
        self._waitForHeaters = True
        heaters = self._printer.get_current_temperatures()
        
        for heater in heaters.keys():
            if float(heaters.get(heater)["target"]) != 0:
                self._logger.info("Turning off heater: %s" % heater)
                self._skipIdleTimer = True
                self._printer.set_temperature(heater, 0)
                self._skipIdleTimer = False
            else:
                self._logger.debug("Heater %s already off." % heater)
        
        while True:
            if not self._waitForHeaters:
                return False
            
            heaters = self._printer.get_current_temperatures()
            
            highest_temp = 0
            heaters_above_waittemp = []
            for heater in heaters.keys():
                if heater == 'bed':
                    continue
                
                temp = float(heaters.get(heater)["actual"])
                self._logger.debug("Heater %s = %sC" % (heater,temp))
                if temp > self.idleTimeoutWaitTemp:
                    heaters_above_waittemp.append(heater)
                
                if temp > highest_temp:
                    highest_temp = temp
                
            if highest_temp <= self.idleTimeoutWaitTemp:
                self._waitForHeaters = False
                return True
            
            self._logger.info("Waiting for heaters(%s) before shutting off PSU..." % ', '.join(heaters_above_waittemp))
            time.sleep(5)

    def hook_gcode_queuing(self, comm_instance, phase, cmd, cmd_type, gcode, *args, **kwargs):
        if gcode:
            if (not self.isPSUOn and self.autoOn and (gcode in self.autoOnCommandsArray)):
                self._logger.info("Auto-On - Turning PSU On (Triggered by %s)" % gcode)
                self.turn_psu_on()

            if self.powerOffWhenIdle and self.isPSUOn and not self._skipIdleTimer:
                if not (gcode in self.idleIgnoreCommandsArray):
                    self._waitForHeaters = False
                    self._start_idle_timer()

    def turn_psu_on(self):
        if self.switchingMethod == 'COMMAND' or self.switchingMethod == 'GPIO' or self.switchingMethod == 'SYSTEM':
            self._logger.info("Switching PSU On")
            if self.switchingMethod == 'COMMAND':
                self._logger.debug("Switching PSU On Using COMMAND: %s" % self.onGCodeCommand)
                self._printer.commands(self.onGCodeCommand)
            elif self.switchingMethod == 'SYSTEM':
                self._logger.debug("Switching PSU On Using SYSTEM: %s" % self.onSysCommand)
                os.system(self.onSysCommand)
            elif self.switchingMethod == 'GPIO':
                self._logger.debug("Switching PSU On Using GPIO: %s" % self.onoffGPIOPin)
                if not self.invertonoffGPIOPin:
                    pin_output=GPIO.HIGH
                else:
                    pin_output=GPIO.LOW

                try:
                    GPIO.output(self.onoffGPIOPin, pin_output)
                except (RuntimeError, ValueError) as e:
                    self._logger.error(e)

            if not self.enableSensing:
                self._noSensing_isPSUOn = True
         
            time.sleep(0.1)
            self.check_psu_state()
        
    def turn_psu_off(self):
        if self.switchingMethod == 'COMMAND' or self.switchingMethod == 'GPIO' or self.switchingMethod == 'SYSTEM':
            self._logger.info("Switching PSU Off")
            if self.switchingMethod == 'COMMAND':
                self._logger.debug("Switching PSU Off Using COMMAND: %s" % self.offGCodeCommand)
                self._printer.commands(self.offGCodeCommand)
            elif self.switchingMethod == 'SYSTEM':
                self._logger.debug("Switching PSU Off Using SYSTEM: %s" % self.offSysCommand)
                os.system(self.offSysCommand)
            elif self.switchingMethod == 'GPIO':
                self._logger.debug("Switching PSU Off Using GPIO: %s" % self.onoffGPIOPin)
                if not self.invertonoffGPIOPin:
                    pin_output=GPIO.LOW
                else:
                    pin_output=GPIO.HIGH
		
                try:
                    GPIO.output(self.onoffGPIOPin, pin_output)
                except (RuntimeError, ValueError) as e:
                    self._logger.error(e)

            if not self.enableSensing:
                self._noSensing_isPSUOn = False
                        
            time.sleep(0.1)
            self.check_psu_state()

    def get_api_commands(self):
        return dict(
            turnPSUOn=[],
            turnPSUOff=[]
        )

    def on_api_command(self, command, data):
        if not user_permission.can():
            return make_response("Insufficient rights", 403)
        
        if command == 'turnPSUOn':
            self.turn_psu_on()
        elif command == 'turnPSUOff':
            self.turn_psu_off()

    def get_settings_defaults(self):
        return dict(
            switchingMethod = '',
            onoffGPIOPin = 0,
            invertonoffGPIOPin = False,
            onGCodeCommand = 'M80', 
            offGCodeCommand = 'M81', 
            onSysCommand = '',
            offSysCommand = '',
            enableSensing = False,
            senseGPIOPin = 0,
            autoOn = False,
            autoOnCommands = "G0,G1,G2,G3,G10,G11,G28,G29,G32,M104,M109,M140,M190",
            powerOffWhenIdle = False,
            idleTimeout = 30,
            idleIgnoreCommands = 'M105',
            idleTimeoutWaitTemp = 50
        )

    def on_settings_save(self, data):
        old_onoffGPIOPin = self.onoffGPIOPin
        old_enableSensing = self.enableSensing
        old_senseGPIOPin = self.senseGPIOPin
        old_switchingMethod = self.switchingMethod
        
        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
        
        self.switchingMethod = self._settings.get(["switchingMethod"])
        self.onoffGPIOPin = self._settings.get_int(["onoffGPIOPin"])
        self.invertonoffGPIOPin = self._settings.get_boolean(["invertonoffGPIOPin"])
        self.onGCodeCommand = self._settings.get(["onGCodeCommand"])
        self.offGCodeCommand = self._settings.get(["offGCodeCommand"])
        self.onSysCommand = self._settings.get(["onSysCommand"])
        self.offSysCommand = self._settings.get(["offSysCommand"])
        self.enableSensing = self._settings.get_boolean(["enableSensing"])
        self.senseGPIOPin = self._settings.get_int(["senseGPIOPin"])
        self.autoOn = self._settings.get_boolean(["autoOn"])
        self.autoOnCommands = self._settings.get(["autoOnCommands"])
        self.autoOnCommandsArray = self.autoOnCommands.split(',')
        self.powerOffWhenIdle = self._settings.get_boolean(["powerOffWhenIdle"])
        self.idleTimeout = self._settings.get_int(["idleTimeout"])
        self.idleIgnoreCommands = self._settings.get(["idleIgnoreCommands"])
        self.idleIgnoreCommandsArray = self.idleIgnoreCommands.split(',')
        self.idleTimeoutWaitTemp = self._settings.get_int(["idleTimeoutWaitTemp"])
        
        if (old_onoffGPIOPin != self.onoffGPIOPin or
           old_senseGPIOPin != self.senseGPIOPin or
           old_enableSensing != self.enableSensing or
           old_switchingMethod != self.switchingMethod):
            self._configure_gpio()

        self._start_idle_timer()

    def get_template_configs(self):
        return [
            dict(type="settings", custom_bindings=False)
        ]

    def get_assets(self):
        return {
            "js": ["js/psucontrol.js"]
        } 

    def get_update_information(self):
        return dict(
            psucontrol=dict(
                displayName="PSU Control",
                displayVersion=self._plugin_version,

                # version check: github repository
                type="github_release",
                user="kantlivelong",
                repo="OctoPrint-PSUControl",
                current=self._plugin_version,

                # update method: pip w/ dependency links
                pip="https://github.com/kantlivelong/OctoPrint-PSUControl/archive/{target_version}.zip"
            )
        )

__plugin_name__ = "PSU Control"

def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = PSUControl()

	global __plugin_hooks__
	__plugin_hooks__ = {
                "octoprint.comm.protocol.gcode.queuing": __plugin_implementation__.hook_gcode_queuing,
		"octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
	}
