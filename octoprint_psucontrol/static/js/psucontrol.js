$(function() {
    function PSUControlViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.isPSUOn = ko.observable();
	self.psu_indicator = undefined;
	self.poweroff_dialog = undefined;

        self.onStartup = function() {
            self.poweroff_dialog = $("#psucontrol_poweroff_confirmation_dialog");
            self.psu_indicator = $("#powercontrol_psu_indicator");
        };

        self.onDataUpdaterPluginMessage = function(plugin, data) {
            if (plugin != "psucontrol") {
                return;
            }

            self.isPSUOn(data.isPSUOn);

            if (self.isPSUOn()) {
                self.psu_indicator.css('color', '#00FF00');
            } else {
                self.psu_indicator.css('color', '#808080');
            }

            if (self.psu_indicator.css('visibility') == "hidden") {
                self.psu_indicator.css('visibility', 'visible');
            }
        };

	self.togglePSU = function() {
            if (self.isPSUOn()) {
                self.showPowerOffDialog();
            } else {
                self.turnPSUOn();
            }
        };

	self.showPowerOffDialog = function() {
            self.poweroff_dialog.modal("show");
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

            self.poweroff_dialog.modal("hide");
        };   
    }

    ADDITIONAL_VIEWMODELS.push([
        PSUControlViewModel,
        ["loginStateViewModel"],
        ["#navbar_plugin_psucontrol"]
    ]);
});
