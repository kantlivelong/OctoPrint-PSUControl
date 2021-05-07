# coding=utf-8

__author__ = "Shawn Bruce <kantlivelong@gmail.com>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2017 Shawn Bruce - Released under terms of the AGPLv3 License"

def commands(cli_group, pass_octoprint_ctx, *args, **kwargs):
    # Requires OctoPrint >= 1.3.5
    import click
    import sys
    import json
    import requests.exceptions
    from octoprint.cli.client import create_client, client_options

    def _api_command(command, apikey, host, port, httpuser, httppass, https, prefix):
        if prefix == None:
            prefix = '/api'

        client = create_client(settings=cli_group.settings,
                               apikey=apikey,
                               host=host,
                               port=port,
                               httpuser=httpuser,
                               httppass=httppass,
                               https=https,
                               prefix=prefix)

        r = client.post_command("plugin/psucontrol", command)
        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError as e:
            click.echo("HTTP Error, got {}".format(e))
            sys.exit(1)

        return r

    @client_options
    @click.command("on")
    def turnPSUOn_command(apikey, host, port, httpuser, httppass, https, prefix):
        """Turn the PSU On"""
        r = _api_command('turnPSUOn', apikey, host, port, httpuser, httppass, https, prefix)

        if r.status_code in [200, 204]:
            click.echo('ok')

    @client_options
    @click.command("off")
    def turnPSUOff_command(apikey, host, port, httpuser, httppass, https, prefix):
        """Turn the PSU Off"""
        r = _api_command('turnPSUOff', apikey, host, port, httpuser, httppass, https, prefix)

        if r.status_code in [200, 204]:
            click.echo('ok')

    @client_options
    @click.command("toggle")
    def togglePSU_command(apikey, host, port, httpuser, httppass, https, prefix):
        """Toggle the PSU On/Off"""
        r = _api_command('togglePSU', apikey, host, port, httpuser, httppass, https, prefix)

        if r.status_code in [200, 204]:
            click.echo('ok')

    @click.option("--return-int", is_flag=True, help="Return the PSU state as a boolean integer.")
    @client_options
    @click.command("status")
    def getPSUState_command(return_int, apikey, host, port, httpuser, httppass, https, prefix):
        """Get the current PSU status"""
        r = _api_command('getPSUState', apikey, host, port, httpuser, httppass, https, prefix)

        if r.status_code in [200, 204]:
            data = json.loads(r._content)

            if return_int:
                click.echo(int(data['isPSUOn']))
            else:
                if data['isPSUOn']:
                    click.echo('on')
                else:
                    click.echo('off')

    return [turnPSUOn_command, turnPSUOff_command, togglePSU_command, getPSUState_command]

