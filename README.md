# OctoPrint PSU Control

This OctoPrint plugin controls an ATX/AUX power supply to help reduce power consumption and noise when the printer is not in use.

Power supply can be automatically switched on when user specified commands are sent to the printer or switched off when idle.

Supports GCode or GPIO to switch power supply on/off.

Requires a Raspberry Pi

![PSUControl](psucontrol_navbar_settings.png?raw=true)

## Setup

Install the plugin using Plugin Manager from Settings

## GPIO Setup

Sense GPIO Pin: Configured as a 3.3v input signal. Use a voltage divider.

On/Off GPIO Pin: Only required if using GPIO instead of GCode to switch the PSU on/off. Configured as a 3.3v output signal. For ATX use a NPN transistor to ground PS_ON. A relay can be used for standard "always on" PSU's

**NOTE: GPIO pins are specified as phsyical number.**
