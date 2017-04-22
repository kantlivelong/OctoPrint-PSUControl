# OctoPrint PSU Control
This OctoPrint plugin controls an ATX/AUX power supply to help reduce power consumption and noise when the printer is not in use.

Power supply can be automatically switched on when user specified commands are sent to the printer and/or switched off when idle.

Supports Commands (G-Code or System) or GPIO to switch power supply on/off.

**Requires a Raspberry Pi**

![PSUControl](psucontrol_navbar_settings.png?raw=true)
 
 
## Setup

Install the plugin using Plugin Manager from Settings
 
 
## GPIO Setup

**NOTE: GPIO pins should be specified as phsyical number and not BCM number.**

###### Sense GPIO Pin
&nbsp;&nbsp;&nbsp;&nbsp; This option is used to determine the on/off state of the power supply instead of assuming based on the last action.

&nbsp;&nbsp;&nbsp;&nbsp; The specified GPIO pin should receive a 3.3v signal from the power supply when it is on and 0v when off. If your power supply does not provide 3.3v then consider using a [Voltage Divider](https://en.wikipedia.org/wiki/Voltage_divider).


###### On/Off GPIO Pin
&nbsp;&nbsp;&nbsp;&nbsp; This option is only required if using GPIO instead of Commands(G-Code) to switch the power supply on/off.

&nbsp;&nbsp;&nbsp;&nbsp; The specified GPIO pin will send a 3.3v signal when turning the power supply on and 0v when off. ATX power supplies can be switched on by grounding the PS_ON pin using a [NPN Transistor](https://en.wikipedia.org/wiki/Bipolar_junction_transistor). For "always on" power supplies use a relay to switch AC mains.

###### On/Off Button GPIO Pin
&nbsp;&nbsp;&nbsp;&nbsp; This option is only required if you want to switch PSU on/off using a physical button connected to a GPIO pin.
&nbsp;&nbsp;&nbsp;&nbsp; If you want to start your Printer without connecting to the OctoPrint Webinterface for printing quickly from SD-Card. You have to wire the button using a pull down resistor. The GPIO internal resistor is set to pull down mode.

![Button with pull down resistor](rpi_pull_down.png?raw=true)

## Troubleshooting
- **The power indicator is out of sync with the power supply state.**

    There are a handful of factors that play into this when not using *Sensing*. Use *Sensing* for the best experience.
 
- **"No access to /dev/mem. Try running as root!"**

    See [Access GPIO pins without root. No access to /dev/mem. Try running as root!](https://raspberrypi.stackexchange.com/questions/40105/access-gpio-pins-without-root-no-access-to-dev-mem-try-running-as-root)
