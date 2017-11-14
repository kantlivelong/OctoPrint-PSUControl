$(function() {
    function PSUControlViewModel(parameters) {
        var self = this;

        self.global_settings = parameters[0];
        self.settings = undefined;
        self.loginState = parameters[1];
        self.isPSUOn = ko.observable(undefined);
        self.psu_indicator = $("#psucontrol_indicator");

        self.onAfterBinding = function() {
            self.settings = self.global_settings.settings.plugins.psucontrol;            
        };

        self.onDataUpdaterPluginMessage = function(plugin, data) {
            if (plugin != "psucontrol") {
                return;
            }

            self.isPSUOn(data.isPSUOn);

            if (self.isPSUOn()) {
                self.psu_indicator.removeClass("off").addClass("on");
            } else {
                self.psu_indicator.removeClass("on").addClass("off");
            }

        };

        self.togglePSU = function() {
            if (self.isPSUOn()) {
                if (self.settings.enablePowerOffWarningDialog()) {
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
        ["#navbar_plugin_psucontrol"]
    ]);
});
