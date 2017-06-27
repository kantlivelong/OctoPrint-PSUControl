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
from flask import make_response, jsonify

class PSUControl(octoprint.plugin.StartupPlugin,
                   octoprint.plugin.TemplatePlugin,
                   octoprint.plugin.AssetPlugin,
                   octoprint.plugin.SettingsPlugin,
                   octoprint.plugin.SimpleApiPlugin):

    def __init__(self):
        self._pin_to_gpio_rev1 = [-1, -1, -1, 0, -1, 1, -1, 4, 14, -1, 15, 17, 18, 21, -1, 22, 23, -1, 24, 10, -1, 9, 25, 11, 8, -1, 7, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1 ]
        self._pin_to_gpio_rev2 = [-1, -1, -1, 2, -1, 3, -1, 4, 14, -1, 15, 17, 18, 27, -1, 22, 23, -1, 24, 10, -1, 9, 25, 11, 8, -1, 7, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1 ]
        self._pin_to_gpio_rev3 = [-1, -1, -1, 2, -1, 3, -1, 4, 14, -1, 15, 17, 18, 27, -1, 22, 23, -1, 24, 10, -1, 9, 25, 11, 8, -1, 7, -1, -1, 5, -1, 6, 12, 13, -1, 19, 16, 26, 20, -1, 21 ]

        self.GPIOMode = ''
        self.switchingMethod = ''
        self.onoffGPIOPin = 0
        self.invertonoffGPIOPin = False
        self.onGCodeCommand = ''
        self.offGCodeCommand = ''
        self.onSysCommand = ''
        self.offSysCommand = ''
        self.postOnDelay = 0.0
        self.autoOn = False
        self.autoOnTriggerGCodeCommands = ''
        self._autoOnTriggerGCodeCommandsArray = []
        self.enablePowerOffWarningDialog = True
        self.powerOffWhenIdle = False
        self.idleTimeout = 0
        self.idleIgnoreCommands = ''
        self._idleIgnoreCommandsArray = []
        self.idleTimeoutWaitTemp = 0
        self.enableSensing = False
        self.disconnectOnPowerOff = False
        self.senseGPIOPin = 0
        self.isPSUOn = False
        self._noSensing_isPSUOn = False
        self._checkPSUTimer = None
        self._idleTimer = None
        self._waitForHeaters = False
        self._skipIdleTimer = False
        self._configuredGPIOPins = []

    def on_settings_initialized(self):
        self.GPIOMode = self._settings.get(["GPIOMode"])
        self._logger.debug("GPIOMode: %s" % self.GPIOMode)

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

        self.postOnDelay = self._settings.get_float(["postOnDelay"])
        self._logger.debug("postOnDelay: %s" % self.postOnDelay)

        self.enableSensing = self._settings.get_boolean(["enableSensing"])
        self._logger.debug("enableSensing: %s" % self.enableSensing)

        self.disconnectOnPowerOff = self._settings.get_boolean(["disconnectOnPowerOff"])
        self._logger.debug("disconnectOnPowerOff: %s" % self.disconnectOnPowerOff)

        self.senseGPIOPin = self._settings.get_int(["senseGPIOPin"])
        self._logger.debug("senseGPIOPin: %s" % self.senseGPIOPin)

        self.autoOn = self._settings.get_boolean(["autoOn"])
        self._logger.debug("autoOn: %s" % self.autoOn)

        self.autoOnTriggerGCodeCommands = self._settings.get(["autoOnTriggerGCodeCommands"])
        self._autoOnTriggerGCodeCommandsArray = self.autoOnTriggerGCodeCommands.split(',')
        self._logger.debug("autoOnTriggerGCodeCommands: %s" % self.autoOnTriggerGCodeCommands)

        self.enablePowerOffWarningDialog = self._settings.get_boolean(["enablePowerOffWarningDialog"])
        self._logger.debug("enablePowerOffWarningDialog: %s" % self.enablePowerOffWarningDialog)

        self.powerOffWhenIdle = self._settings.get_boolean(["powerOffWhenIdle"])
        self._logger.debug("powerOffWhenIdle: %s" % self.powerOffWhenIdle)

        self.idleTimeout = self._settings.get_int(["idleTimeout"])
        self._logger.debug("idleTimeout: %s" % self.idleTimeout)

        self.idleIgnoreCommands = self._settings.get(["idleIgnoreCommands"])
        self._idleIgnoreCommandsArray = self.idleIgnoreCommands.split(',')
        self._logger.debug("idleIgnoreCommands: %s" % self.idleIgnoreCommands)

        self.idleTimeoutWaitTemp = self._settings.get_int(["idleTimeoutWaitTemp"])
        self._logger.debug("idleTimeoutWaitTemp: %s" % self.idleTimeoutWaitTemp)

        self._configure_gpio()

        self._checkPSUTimer = RepeatedTimer(5.0, self.check_psu_state, None, None, True)
        self._checkPSUTimer.start()

        self._start_idle_timer()

    def _gpio_board_to_bcm(self, pin):
        if GPIO.RPI_REVISION == 1:
            pin_to_gpio = self._pin_to_gpio_rev1
        elif GPIO.RPI_REVISION == 2:
            pin_to_gpio = self._pin_to_gpio_rev2
        else:
            pin_to_gpio = self._pin_to_gpio_rev3

        return pin_to_gpio[pin]

    def _gpio_bcm_to_board(self, pin):
        if GPIO.RPI_REVISION == 1:
            pin_to_gpio = self._pin_to_gpio_rev1
        elif GPIO.RPI_REVISION == 2:
            pin_to_gpio = self._pin_to_gpio_rev2
        else:
            pin_to_gpio = self._pin_to_gpio_rev3

        return pin_to_gpio.index(pin)

    def _gpio_get_pin(self, pin):
        if (GPIO.getmode() == GPIO.BOARD and self.GPIOMode == 'BOARD') or (GPIO.getmode() == GPIO.BCM and self.GPIOMode == 'BCM'):
            return pin
        elif GPIO.getmode() == GPIO.BOARD and self.GPIOMode == 'BCM':
            return self._gpio_bcm_to_board(pin)
        elif GPIO.getmode() == GPIO.BCM and self.GPIOMode == 'BOARD':
            return self._gpio_board_to_bcm(pin)
        else:
            return 0

    def _configure_gpio(self):
        self._logger.info("Running RPi.GPIO version %s" % GPIO.VERSION)
        if GPIO.VERSION < "0.6":
            self._logger.error("RPi.GPIO version 0.6.0 or greater required.")
        
        GPIO.setwarnings(False)

        for pin in self._configuredGPIOPins:
            self._logger.debug("Cleaning up pin %s" % pin)
            try:
                GPIO.cleanup(self._gpio_get_pin(pin))
            except (RuntimeError, ValueError) as e:
                self._logger.error(e)
        self._configuredGPIOPins = []

        if GPIO.getmode() is None:
            if self.GPIOMode == 'BOARD':
                GPIO.setmode(GPIO.BOARD)
            elif self.GPIOMode == 'BCM':
                GPIO.setmode(GPIO.BCM)
            else:
                return
        
        if self.enableSensing:
            self._logger.info("Using sensing to determine PSU on/off state.")
            self._logger.info("Configuring GPIO for pin %s" % self.senseGPIOPin)
            try:
                GPIO.setup(self._gpio_get_pin(self.senseGPIOPin), GPIO.IN)
                self._configuredGPIOPins.append(self.senseGPIOPin)
            except (RuntimeError, ValueError) as e:
                self._logger.error(e)
        
        if self.switchingMethod == 'GCODE':
            self._logger.info("Using G-Code Commands for On/Off")
        elif self.switchingMethod == 'SYSTEM':
            self._logger.info("Using System Commands for On/Off")
        elif self.switchingMethod == 'GPIO':
            self._logger.info("Using GPIO for On/Off")
            self._logger.info("Configuring GPIO for pin %s" % self.onoffGPIOPin)
            try:
                GPIO.setup(self._gpio_get_pin(self.onoffGPIOPin), GPIO.OUT)
                self._configuredGPIOPins.append(self.onoffGPIOPin)
            except (RuntimeError, ValueError) as e:
                self._logger.error(e)

    def check_psu_state(self):
        old_isPSUOn = self.isPSUOn

        if self.enableSensing:
            self._logger.debug("Polling PSU state...")
            r = 0
            try:
                r = GPIO.input(self._gpio_get_pin(self.senseGPIOPin))
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
            if (not self.isPSUOn and self.autoOn and (gcode in self._autoOnTriggerGCodeCommandsArray)):
                self._logger.info("Auto-On - Turning PSU On (Triggered by %s)" % gcode)
                self.turn_psu_on()

            if self.powerOffWhenIdle and self.isPSUOn and not self._skipIdleTimer:
                if not (gcode in self._idleIgnoreCommandsArray):
                    self._waitForHeaters = False
                    self._start_idle_timer()

    def turn_psu_on(self):
        if self.switchingMethod == 'GCODE' or self.switchingMethod == 'GPIO' or self.switchingMethod == 'SYSTEM':
            self._logger.info("Switching PSU On")
            if self.switchingMethod == 'GCODE':
                self._logger.debug("Switching PSU On Using GCODE: %s" % self.onGCodeCommand)
                self._printer.commands(self.onGCodeCommand)
            elif self.switchingMethod == 'SYSTEM':
                self._logger.debug("Switching PSU On Using SYSTEM: %s" % self.onSysCommand)
                r = os.system(self.onSysCommand)
                self._logger.debug("System command returned: %s" % r)
            elif self.switchingMethod == 'GPIO':
                self._logger.debug("Switching PSU On Using GPIO: %s" % self.onoffGPIOPin)
                if not self.invertonoffGPIOPin:
                    pin_output=GPIO.HIGH
                else:
                    pin_output=GPIO.LOW

                try:
                    GPIO.output(self._gpio_get_pin(self.onoffGPIOPin), pin_output)
                except (RuntimeError, ValueError) as e:
                    self._logger.error(e)

            if not self.enableSensing:
                self._noSensing_isPSUOn = True
         
            time.sleep(0.1 + self.postOnDelay)
            self.check_psu_state()
        
    def turn_psu_off(self):
        if self.switchingMethod == 'GCODE' or self.switchingMethod == 'GPIO' or self.switchingMethod == 'SYSTEM':
            self._logger.info("Switching PSU Off")
            if self.switchingMethod == 'GCODE':
                self._logger.debug("Switching PSU Off Using GCODE: %s" % self.offGCodeCommand)
                self._printer.commands(self.offGCodeCommand)
            elif self.switchingMethod == 'SYSTEM':
                self._logger.debug("Switching PSU Off Using SYSTEM: %s" % self.offSysCommand)
                r = os.system(self.offSysCommand)
                self._logger.debug("System command returned: %s" % r)
            elif self.switchingMethod == 'GPIO':
                self._logger.debug("Switching PSU Off Using GPIO: %s" % self.onoffGPIOPin)
                if not self.invertonoffGPIOPin:
                    pin_output=GPIO.LOW
                else:
                    pin_output=GPIO.HIGH
		
                try:
                    GPIO.output(self._gpio_get_pin(self.onoffGPIOPin), pin_output)
                except (RuntimeError, ValueError) as e:
                    self._logger.error(e)

            if self.disconnectOnPowerOff:
                self._printer.disconnect()
                
            if not self.enableSensing:
                self._noSensing_isPSUOn = False
                        
            time.sleep(0.1)
            self.check_psu_state()

    def get_api_commands(self):
        return dict(
            turnPSUOn=[],
            turnPSUOff=[],
            togglePSU=[],
            getPSUState=[]
        )

    def on_api_command(self, command, data):
        if not user_permission.can():
            return make_response("Insufficient rights", 403)
        
        if command == 'turnPSUOn':
            self.turn_psu_on()
        elif command == 'turnPSUOff':
            self.turn_psu_off()
        elif command == 'togglePSU':
            if self.isPSUOn:
                self.turn_psu_off()
            else:
                self.turn_psu_on()
        elif command == 'getPSUState':
            return jsonify(isPSUOn=self.isPSUOn)

    def get_settings_defaults(self):
        return dict(
            GPIOMode = 'BOARD',
            switchingMethod = '',
            onoffGPIOPin = 0,
            invertonoffGPIOPin = False,
            onGCodeCommand = 'M80', 
            offGCodeCommand = 'M81', 
            onSysCommand = '',
            offSysCommand = '',
            postOnDelay = 0.0,
            enableSensing = False,
            disconnectOnPowerOff = False,
            senseGPIOPin = 0,
            autoOn = False,
            autoOnTriggerGCodeCommands = "G0,G1,G2,G3,G10,G11,G28,G29,G32,M104,M109,M140,M190",
            enablePowerOffWarningDialog = True,
            powerOffWhenIdle = False,
            idleTimeout = 30,
            idleIgnoreCommands = 'M105',
            idleTimeoutWaitTemp = 50
        )

    def on_settings_save(self, data):
        old_GPIOMode = self.GPIOMode
        old_onoffGPIOPin = self.onoffGPIOPin
        old_enableSensing = self.enableSensing
        old_senseGPIOPin = self.senseGPIOPin
        old_switchingMethod = self.switchingMethod
        
        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
        
        self.GPIOMode = self._settings.get(["GPIOMode"])
        self.switchingMethod = self._settings.get(["switchingMethod"])
        self.onoffGPIOPin = self._settings.get_int(["onoffGPIOPin"])
        self.invertonoffGPIOPin = self._settings.get_boolean(["invertonoffGPIOPin"])
        self.onGCodeCommand = self._settings.get(["onGCodeCommand"])
        self.offGCodeCommand = self._settings.get(["offGCodeCommand"])
        self.onSysCommand = self._settings.get(["onSysCommand"])
        self.offSysCommand = self._settings.get(["offSysCommand"])
        self.postOnDelay = self._settings.get_float(["postOnDelay"])
        self.enableSensing = self._settings.get_boolean(["enableSensing"])
        self.disconnectOnPowerOff = self._settings.get_boolean(["disconnectOnPowerOff"])
        self.senseGPIOPin = self._settings.get_int(["senseGPIOPin"])
        self.autoOn = self._settings.get_boolean(["autoOn"])
        self.autoOnTriggerGCodeCommands = self._settings.get(["autoOnTriggerGCodeCommands"])
        self._autoOnTriggerGCodeCommandsArray = self.autoOnTriggerGCodeCommands.split(',')
        self.powerOffWhenIdle = self._settings.get_boolean(["powerOffWhenIdle"])
        self.idleTimeout = self._settings.get_int(["idleTimeout"])
        self.idleIgnoreCommands = self._settings.get(["idleIgnoreCommands"])
        self.enablePowerOffWarningDialog = self._settings.get_boolean(["enablePowerOffWarningDialog"])
        self._idleIgnoreCommandsArray = self.idleIgnoreCommands.split(',')
        self.idleTimeoutWaitTemp = self._settings.get_int(["idleTimeoutWaitTemp"])
        
        if (old_GPIOMode != self.GPIOMode or
           old_onoffGPIOPin != self.onoffGPIOPin or
           old_senseGPIOPin != self.senseGPIOPin or
           old_enableSensing != self.enableSensing or
           old_switchingMethod != self.switchingMethod):
            self._configure_gpio()

        self._start_idle_timer()

    def get_settings_version(self):
        return 2

    def on_settings_migrate(self, target, current=None):
        if current is None or current < 2:
            # v2 changes names of settings variables to accomidate system commands.
            cur_switchingMethod = self._settings.get(["switchingMethod"])
            if cur_switchingMethod is not None and cur_switchingMethod == "COMMAND":
                self._logger.info("Migrating Setting: switchingMethod=COMMAND -> switchingMethod=GCODE")
                self._settings.set(["switchingMethod"], "GCODE")

            cur_onCommand = self._settings.get(["onCommand"])
            if cur_onCommand is not None:
                self._logger.info("Migrating Setting: onCommand={0} -> onGCodeCommand={0}".format(cur_onCommand))
                self._settings.set(["onGCodeCommand"], cur_onCommand)
                self._settings.remove(["onCommand"])
            
            cur_offCommand = self._settings.get(["offCommand"])
            if cur_offCommand is not None:
                self._logger.info("Migrating Setting: offCommand={0} -> offGCodeCommand={0}".format(cur_offCommand))
                self._settings.set(["offGCodeCommand"], cur_offCommand)
                self._settings.remove(["offCommand"])

            cur_autoOnCommands = self._settings.get(["autoOnCommands"])
            if cur_autoOnCommands is not None:
                self._logger.info("Migrating Setting: autoOnCommands={0} -> autoOnTriggerGCodeCommands={0}".format(cur_autoOnCommands))
                self._settings.set(["autoOnTriggerGCodeCommands"], cur_autoOnCommands)
                self._settings.remove(["autoOnCommands"])

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
