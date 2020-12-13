$(function() {
    function PSUControlViewModel(parameters) {
        var self = this;

        self.settingsViewModel = parameters[0]
        self.loginState = parameters[1];
        
        self.settings = undefined;
        self.scripts_gcode_psucontrol_post_on = ko.observable(undefined);
        self.scripts_gcode_psucontrol_pre_off = ko.observable(undefined);

        self.hasGPIO = ko.observable(true);
        self.isPSUOn = ko.observable(undefined);

        self.psu_indicator = $("#psucontrol_indicator");

        self.onBeforeBinding = function() {
            self.settings = self.settingsViewModel.settings;
        };

        self.onSettingsShown = function () {
            self.scripts_gcode_psucontrol_post_on(self.settings.scripts.gcode["psucontrol_post_on"]());
            self.scripts_gcode_psucontrol_pre_off(self.settings.scripts.gcode["psucontrol_pre_off"]());
        };

        self.onSettingsHidden = function () {
            self.settings.plugins.psucontrol.scripts_gcode_psucontrol_post_on = null;
            self.settings.plugins.psucontrol.scripts_gcode_psucontrol_pre_off = null;
        };

        self.onSettingsBeforeSave = function () {
            if (self.scripts_gcode_psucontrol_post_on() != self.settings.scripts.gcode["psucontrol_post_on"]()) {
                self.settings.plugins.psucontrol.scripts_gcode_psucontrol_post_on = self.scripts_gcode_psucontrol_post_on;
                self.settings.scripts.gcode["psucontrol_post_on"](self.scripts_gcode_psucontrol_post_on());
            }

            if (self.scripts_gcode_psucontrol_pre_off() != self.settings.scripts.gcode["psucontrol_pre_off"]()) {
                self.settings.plugins.psucontrol.scripts_gcode_psucontrol_pre_off = self.scripts_gcode_psucontrol_pre_off;
                self.settings.scripts.gcode["psucontrol_pre_off"](self.scripts_gcode_psucontrol_pre_off());
            }
        };

        self.onStartup = function () {
            self.isPSUOn.subscribe(function() {
                if (self.isPSUOn()) {
                    self.psu_indicator.removeClass("off").addClass("on");
                } else {
                    self.psu_indicator.removeClass("on").addClass("off");
                }   
            });
            
            $.ajax({
                url: API_BASEURL + "plugin/psucontrol",
                type: "POST",
                dataType: "json",
                data: JSON.stringify({
                    command: "getPSUState"
                }),
                contentType: "application/json; charset=UTF-8"
            }).done(function(data) {
                self.isPSUOn(data.isPSUOn);
            });
        }

        self.onDataUpdaterPluginMessage = function(plugin, data) {
            if (plugin != "psucontrol") {
                return;
            }

            if (data.hasGPIO !== undefined) {
                self.hasGPIO(data.hasGPIO);
            }

            if (data.isPSUOn !== undefined) {
                self.isPSUOn(data.isPSUOn);
            }
        };

        self.togglePSU = function() {
            if (self.isPSUOn()) {
                if (self.settings.plugins.psucontrol.enablePowerOffWarningDialog()) {
                    showConfirmationDialog({
                        message: "You are about to turn off the PSU.",
                        onproceed: function() {
                            self.turnPSUOff();
                        }
                    });
                } else {
                    self.turnPSUOff();
                }
            } else {
                self.turnPSUOn();
            }
        };

        self.turnPSUOn = function() {
            $.ajax({
                url: API_BASEURL + "plugin/psucontrol",
                type: "POST",
                dataType: "json",
                data: JSON.stringify({
                    command: "turnPSUOn"
                }),
                contentType: "application/json; charset=UTF-8"
            })
        };

    	self.turnPSUOff = function() {
            $.ajax({
                url: API_BASEURL + "plugin/psucontrol",
                type: "POST",
                dataType: "json",
                data: JSON.stringify({
                    command: "turnPSUOff"
                }),
                contentType: "application/json; charset=UTF-8"
            })
        };   
    }

    ADDITIONAL_VIEWMODELS.push([
        PSUControlViewModel,
        ["settingsViewModel", "loginStateViewModel"],
        ["#navbar_plugin_psucontrol", "#settings_plugin_psucontrol"]
    ]);
});
