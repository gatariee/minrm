#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# a minimal winrm client with tab autocomplete and colors
#

import warnings
warnings.filterwarnings( "ignore" )

import argparse
import shlex
import readline

from colorama import Fore, Style, init as colorama_init
from pypsrp.powershell import PowerShell, RunspacePool
from pypsrp.wsman import WSMan

colorama_init()

COMMANDS = []
HELP = f"""
Available commands:
    [!] runs something remotely, use with caution! (OPSEC)
        ...
            
    [+] does not run any command remotely!
        cmdlets       - returns names of cached cmdlets
        info <cmdlet> - returns information about a cmdlet
        help          - show this help
        exit          - exit the shell
"""


def PRINT( type: str, msg: str, debug: bool = False ):
    if debug:
        colors = { "+": Fore.GREEN, "*": Fore.YELLOW, "!": Fore.RED }
        print( f"{colors.get(type, Fore.WHITE)}[{type}]{Style.RESET_ALL} {msg}" )


def init( wsman: WSMan ) -> bool:
    global COMMANDS
    try:
        ps = execute( wsman, "Get-Command" )
        for line in ps.output:
            COMMANDS.append( line )
        return True
    except Exception as e:
        print( e )
        return False


def execute( wsman: WSMan, command: str ) -> PowerShell:
    with RunspacePool( wsman ) as pool:
        ps = PowerShell( pool )
        tokens = shlex.split( command, posix = False )
        cmdlet = tokens[ 0 ]
        ps.add_cmdlet( cmdlet )

        i = 1
        while i < len( tokens ):
            token = tokens[ i ]

            if token.startswith( '-' ):
                param_name = token.lstrip( '-' )
                if i + 1 < len( tokens ) and not tokens[ i + 1 ].startswith( '-' ):
                    param_value = tokens[ i + 1 ]
                    ps.add_parameter( param_name, param_value )
                    i += 2
                else:
                    ps.add_parameter( param_name, None )
                    i += 1
            else:
                ps.add_argument( token )
                i += 1

        ps.invoke()
        return ps


def completer( text, state ):
    options = [
        cmd.adapted_properties[ 'Name' ] for cmd in COMMANDS
        if cmd.adapted_properties[ 'Name' ].lower().startswith( text.lower() )
    ]
    builtin_commands = [ "info", "cmdlets", "help", "exit" ]
    options += [ cmd for cmd in builtin_commands if cmd.lower().startswith( text.lower() ) ]
    options = sorted( set( options ) )
    return options[ state ] if state < len( options ) else None

def main():
    parser = argparse.ArgumentParser( add_help = True, description = "a minimal winrm client in python, author: @gatari" )

    parser.add_argument( "-i", "--ip", help = "ip address or hostname", required = True )
    parser.add_argument( "-u", "--user", required = True , help = "username (i.e. Administrator)" )
    parser.add_argument( "-p", "--password", required = False , help = "cleartext password, uses negotiate auth" )
    parser.add_argument( "-H", "--hash", required = False , help = "NTLM hash, uses ntlm auth" )
    parser.add_argument( "-S", "--ssl", required = False, help = "Enable SSL" , action='store_true' )

    args = parser.parse_args()
    if args.password is None and args.hash is None:
        parser.error( "password or hash is required" )

    USER = args.user
    CREDENTIAL = f"{args.password}" if args.password else f"{'f'*32}:{args.hash}"
    HOST = args.ip
    AUTH = "negotiate" if args.password else "ntlm"
    SSL  = True if args.ssl else False

    PRINT( "+", f"Creating WSMan object for {USER}@{HOST}", debug = True )
    wsman = WSMan( server = HOST,
                   username = USER,
                   password = CREDENTIAL,
                   auth = AUTH,
                   ssl = SSL,
                   cert_validation = False )
    PRINT( "*", f"Verifying connection to {USER}@{HOST}", debug = True )

    if not init( wsman ):
        PRINT( "!", f"Failed to connect to {USER}@{HOST}", debug = True )
        exit( 1 )

    PRINT( "+", f"Connected to {USER}@{HOST}", debug = True )
    PRINT( "!", f"be careful with what you execute! this is not a real shell", debug = True )

    readline.parse_and_bind( "tab: complete" )
    readline.set_completer( completer )

    PREFIX = f"[{USER}@{HOST}]".lower()
    while True:
        try:
            command = input( f"{Fore.CYAN}{PREFIX}{Style.RESET_ALL} {Fore.BLUE}PS>{Style.RESET_ALL} " )
            match command.split()[ 0 ]:
                case "":
                    continue

                case "exit":
                    break

                case "clear":
                    print( "\033[H\033[J" )

                case "cmdlets":
                    print( "Available cmdlets:" )
                    for cmdlet in COMMANDS:
                        print( f"  {Fore.GREEN}{cmdlet.adapted_properties['Name']}{Style.RESET_ALL}" )

                case "info":
                    cmdlet = command.split()[ 1: ]
                    if len( cmdlet ) == 0:
                        print( "usage: info <cmdlet>" )
                        continue
                    for c in COMMANDS:
                        if c.adapted_properties[ 'Name' ] == cmdlet[ 0 ]:
                            print( f"{Fore.GREEN}Name:{Style.RESET_ALL} {c.adapted_properties['Name']}" )
                            print( f"{Fore.GREEN}Definition:{Style.RESET_ALL} {c.adapted_properties['Definition']}" )
                            break
                    else:
                        print( f"{Fore.RED}cmdlet '{cmdlet[0]}' not found{Style.RESET_ALL}" )

                case "help":
                    print( HELP )
                case _:
                    ps = execute( wsman, command )

                    if ps.had_errors:
                        print( f"{Fore.RED}Error:{Style.RESET_ALL}" )
                        for line in ps.streams.error:
                            print( line )
                        print()

                    print( f"{Fore.GREEN}Output:{Style.RESET_ALL}" )
                    for line in ps.output:
                        print( line )
                    print()
        except KeyboardInterrupt:
            print( "\nExiting..." )
            break
        except Exception as e:
            print( e )


if __name__ == "__main__":
    main()
