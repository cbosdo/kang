#!/usr/bin/python3
# -*- coding: utf-8 -*-

import kang.relays
import kang.scheduler
import kang.sim800

import json
import locale
import logging
import os.path
import re
import sys
import time

AUTH_FILE = os.path.expanduser('authorized.txt')
CONFIG_FILE = os.path.expanduser('kang.json')
EVENTS_FILE = os.path.expanduser('events.txt')

log = logging.getLogger(__name__)

scheduler_thread = kang.scheduler.SchedulerThread(EVENTS_FILE, [kang.relays.start, kang.relays.stop])


def is_authorized(sender):
    """
    @return: True if the sender is contained in the authorized file
    """
    with open(AUTH_FILE, 'r') as auth_fd:
        return '%s\n' % sender in auth_fd.readlines()


def load_configuration():
    """
    Load and apply the configuration from kang.json
    """
    config = {}
    if os.path.isfile(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as config_fd:
            try:
                config = json.loads(config_fd.read())
            except:
                log.error('Failed to load configuration from %s', CONFIG_FILE)

    level = config.get('log_level', 'warning')
    all_levels = [logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR]
    matching = [lvl for lvl in all_levels if logging.getLevelName(lvl).lower() == level.lower()]
    logging.basicConfig(
            format='%(asctime)s:%(levelname)s:%(message)s',
            level=matching[0] if matching else logging.WARNING)

    return config

ACCENTS_MAP = {
    "[éèêë]": "e",
    "[àâ]": "a",
}

COMMANDS = [
    {
        "pattern": re.compile("^(?:demarrer?|allumer?)$", re.IGNORECASE),
        "fn": "start_heating",
        "command": "Démarrer",
        "help": "démarre le chauffage dans l'église et le hall",
        "help_group": "démarrer",
    },
    {
        "pattern": re.compile(r"^(?:demarrer?|allumer?)(?: dans (?P<place>.+))? le (?P<day>[0-9]{1,2})(?:[ /](?P<month>\w+|[0-9]{1,2})(?:[ /](?P<year>20[0-9]{2}))?)? a (?P<hour>[0-9]{1,2})[h:](?:(?P<min>[0-9]{1,2}))? pendant (?P<duration>[0-9]+)h$", re.IGNORECASE),
        "fn": "schedule_heating",
        "command": "Démarrer dans ... le ... à ... pendant ...h",
        "help": "Programme le chauffage",
        "help_group": "programmer",
    },
    {
            "pattern": re.compile(r"^annuler?(?: dans (?P<place>.+))? le (?P<day>[0-9]{1,2})(?:[ /](?P<month>\w+|[0-9]{1,2})(?:[ /](?P<year>20[0-9]{2}))?)? a (?P<hour>[0-9]{1,2})[h:](?:(?P<min>[0-9]{1,2}))? pendant (?P<duration>[0-9]+)h$", re.IGNORECASE),
        "fn": "cancel_heating",
        "command": "Annuler dans ... le ... à ... pendant ...h",
        "help": "Annule la programmation du chauffage",
        "help_group": "programmer",
    },
    {
        "pattern": re.compile("^(?:demarrer?|allumer?) dans (?P<place>.+)$", re.IGNORECASE),
        "fn": "start_heating",
        "command": "Démarrer dans ...",
        "help": "démarre le chauffage dans l'église ou le hall",
        "help_group": "démarrer",
    },
    {
        "pattern": re.compile("^(?:arreter?|eteindre|eteind)$", re.IGNORECASE),
        "fn": "stop_heating",
        "command": "Arrêter",
        "help": "arrête le chauffage dans l'église et le hall",
        "help_group": "arrêter",
    },
    {
        "pattern": re.compile("^(?:arreter?|eteindre|eteind) dans (?P<place>.+)$", re.IGNORECASE),
        "fn": "stop_heating",
        "command": "Arrêter dans ...",
        "help": "arrête le chauffage dans l'église ou dans le hall",
        "help_group": "arrêter",
    },
    {
        "pattern": re.compile("^(?:programmation|lister)$", re.IGNORECASE),
        "fn": "list_events",
        "command": "Lister",
        "help": "Liste des commandes programmées",
        "help_group": "programmer",
    },
    {
        "pattern": re.compile(r"^ajouter? (\+?[0-9. -]+) aux numeros autorises$", re.IGNORECASE),
        "fn": "add_authorized",
        "command": "Ajouter 06... aux numéros autorisés",
        "help": "autorise le numéro à utiliser le système",
        "help_group": "administrer",
    },
    {
        "pattern": re.compile(r"^supprimer? (\+?[0-9. -]+) des numeros autorises$", re.IGNORECASE),
        "fn": "remove_authorized",
        "command": "Supprimer 06... des numéros autorisés",
        "help": "ne plus autoriser le numéro à utiliser le système",
        "help_group": "administrer",
    },
    {
        "pattern": re.compile("^(?:aide|help)(?: ([a-z]+))?$", re.IGNORECASE),
        "fn": "help",
        "command": "Aide ...",
        "help": "Fourni de l'aide sur une commande",
    },
    {
        "pattern": re.compile("^merci$", re.IGNORECASE),
        "fn": "thanks",
    },
]


def thanks(dest):
    """
    Be polite
    """
    return kang.sim800.Sms(dest, "De rien !")


def help(dest, matcher):
    """
    Display the help in a returned SMS

    :param dest: number to send the SMS to
    """
    commands_help = {f"\u25AA Aide {cmd.get('help_group')}" for cmd in COMMANDS if cmd.get("help_group")}
    if matcher.group(1):
        commands_help = [
            "\u25AA {}".format(cmd["command"])
            for cmd
            in COMMANDS
            if cmd.get("help_group") == matcher.group(1)
        ]

    message = "Taper une des {} commandes suivantes:\n{}".format(len(commands_help), "\n".join(commands_help))
    return kang.sim800.Sms(dest, message)


def _get_places(matcher):
    """
    Convert the text sent by the user into a known place
    """
    places = []
    if matcher and matcher.group("place") is not None:
        place_input = matcher.group("place").lower()
        if place_input in ["l'église", "l'eglise"]:
            places = [kang.relays.CHURCH]
        elif place_input in ["le hall"]:
            places = [kang.relays.HALL]
    else:
        places = [kang.relays.CHURCH, kang.relays.HALL]
    return places


def _get_date_time(matcher):
    """
    Parse the input date into a struct_time
    """
    now = time.localtime()
    day = int(matcher.group("day"))
    month = matcher.group("month") or now.tm_mon
    try:
        month = int(month)
    except ValueError:
        month = time.strptime(month, "%B").tm_mon
    year = int(matcher.group("year") or now.tm_year)

    hour = int(matcher.group("hour"))
    minute = int(matcher.group("min") or "0") 

    return time.mktime((year, month, day, hour, minute, 0, 0, 1, -1))


def _format_places(places):
    """
    Convert the places into user-readable strings
    """
    place_map = {kang.relays.CHURCH: "l'église", kang.relays.HALL: "le hall"}
    return [place_map[place] for place in places]


def start_heating(dest, matcher=None):
    """
    Trigger the heating start or schedule it

    :param dest: the number sending the command
    :param matcher: the regexp matcher with the groups
    """
    places = _get_places(matcher)
    for place in places:
        kang.relays.start(place)
    
    return kang.sim800.Sms(dest, "Démarré dans {}".format(
        ", ".join(_format_places(places))
    ))


def stop_heating(dest, matcher=None):
    """
    Trigger the heating stop

    :param dest: the number sending the command
    :param matcher: the regexp matcher with the groups
    """
    places = _get_places(matcher)
    for place in places:
        kang.relays.stop(place)

    return kang.sim800.Sms(dest, "Arrêté dans {}".format(
        ", ".join(_format_places(places))
    ))


def schedule_heating(dest, matcher):
    """
    Schedule the start and stop of the heating

    :param dest: the number sending the command
    :param matcher: the regexp matcher with the groups
    """
    places = _get_places(matcher)
    start_time = _get_date_time(matcher)

    # Heating duration in hours
    duration = int(matcher.group("duration"))
    stop_time = start_time + duration * 3600

    for place in places:
        scheduler_thread.enterabs(start_time, 0, kang.relays.start, argument=(place,))
        scheduler_thread.enterabs(stop_time, 0, kang.relays.stop, argument=(place,))

    return kang.sim800.Sms(dest, "Programmé dans {}".format(
        ", ".join(_format_places(places))
    ))


def cancel_heating(dest, matcher):
    """
    Cancel the start and stop of the heating

    :param dest: the number sending the command
    :param matcher: the regexp matcher with the groups
    """
    places = _get_places(matcher)
    start_time = _get_date_time(matcher)

    # Heating duration in hours
    duration = int(matcher.group("duration"))
    stop_time = start_time + duration * 3600

    errors = {}
    for place in places:
        try:
            scheduler_thread.cancel(start_time, kang.relays.start, argument=(place,))
        except ValueError:
            place_errors = errors.get(place, [])
            place_errors.append(time.strftime("%d/%m/%Y %H:%M", time.localtime(start_time)))
            errors[place] = place_errors

        try:
            scheduler_thread.cancel(stop_time, kang.relays.stop, argument=(place,))
        except ValueError:
            place_errors = errors.get(place, [])
            place_errors.append(time.strftime("%d/%m/%Y %H:%M", time.localtime(stop_time)))
            errors[place] = place_errors

    if errors:
        error_messages = ["\u25AA {}: {}\n".format(_format_places([place])[0], ", ".join(errors[place])) for place in errors.keys()]
        return kang.sim800.Sms(dest, "Annulé sauf:\n{}".format(",".join(error_messages)))
    return kang.sim800.Sms(dest, "Démarrage et arret annulés")


def cut(l, n):
    n = max(1, n)
    return [l[i:i+n] for i in range(0, len(l), n)]

def list_events(dest):
    """
    List the scheduled events

    :param dest: the number sending the command
    """
    events = scheduler_thread.events
    if events:
        name_map = {
            kang.relays.start: "démarrer",
            kang.relays.stop: "arrêter",
        }
        messages = []
        chunks = cut(events, 4)
        for i, batch in enumerate(chunks):
            events_message = [
                "\u25AA {}: {} - {}".format(
                    time.strftime('%d/%m/%Y %H:%M', time.localtime(event.time)),
                    name_map[event.action],
                    ''.join(_format_places(event.argument))
                )
                for event
                in batch
            ]
            messages.append(kang.sim800.Sms(dest, "Programmation {}/{}:\n{}".format(i + 1, len(chunks), '\n'.join(events_message))))
        return messages
    return kang.sim800.Sms(dest, "Aucune programmation")


def add_authorized(dest, matcher):
    """
    Add a number to the authorized file

    :param dest: the number sending the command
    :param matcher: the regexp matcher with the groups
    """
    new_number = re.sub("[ .-]", "", matcher.group(1))
    if new_number.startswith("00"):
        new_number = "+{}".format(new_number[2:])
    if not new_number.startswith("+"):
        new_number = "+33{}".format(new_number.lstrip("0"))

    log.debug("Adding number {} to authorized".format(new_number))
    
    with open(AUTH_FILE, 'r+') as auth_fd:
        all_numbers = auth_fd.readlines()
        if "{}\n".format(new_number) in all_numbers:
            return kang.sim800.Sms(dest, "Numéro déjà autorisé")

        all_numbers.append("{}\n".format(new_number))
        auth_fd.seek(0)
        auth_fd.write("".join(all_numbers))
        auth_fd.truncate()
    return kang.sim800.Sms(dest, "Numéro ajouté")


def remove_authorized(dest, matcher):
    """
    Remove a number from the authorized file

    :param dest: the number sending the command
    :param matcher: the regexp matcher with the groups
    """
    number = re.sub("[ .-]", "", matcher.group(1))
    if number.startswith("00"):
        number = "+{}".format(number[2:])
    if not number.startswith("+"):
        number = "+33{}".format(number.lstrip("0"))
    
    log.debug("Removing number {} from authorized".format(number))

    with open(AUTH_FILE, 'r+') as auth_fd:
        all_numbers = auth_fd.readlines()
        if "{}\n".format(number) not in all_numbers:
            return kang.sim800.Sms(dest, "Numéro déjà pas autorisé")

        all_numbers.remove("{}\n".format(number))
        auth_fd.seek(0)
        auth_fd.write("".join(all_numbers))
        auth_fd.truncate()
    return kang.sim800.Sms(dest, "Numéro supprimé")


def process_command(sms, sim):
    """
    Process the received message and trigger the proper action
    """
    # Replace the accented characters
    message = sms.message.lower()
    for pattern, repl in ACCENTS_MAP.items():
        message = re.sub(pattern, repl, message)

    for cmd in COMMANDS:
        matcher = cmd["pattern"].fullmatch(message)
        if matcher:
            if cmd["pattern"].groups > 0:
                response = globals()[cmd["fn"]](sms.number, matcher)
            else:
                response = globals()[cmd["fn"]](sms.number)

            # Send the response SMS if needed
            if response and isinstance(response, list):
                for messages in response:
                    messages.send(sim)
            else:
                response.send(sim)
            break


def main():
    locale.setlocale(locale.LC_ALL, 'fr_FR.utf-8')
    config = load_configuration()
    log.info("Starting")
    sim = kang.sim800.setup()
    kang.relays.setup()

    scheduler_thread.start()

    ret = 0
    while True:
        try:
            ids = kang.sim800.getAllSmsIds(sim)
            for idx in ids:
                sms = kang.sim800.Sms.read(sim, idx)
                try:
                    if is_authorized(sms.number):
                        process_command(sms, sim)
                finally:
                    # Remove the message to avoid processing twice
                    # Also remove if the message triggered an error while processing
                    kang.sim800.Sms.delete(sim, idx)
                
                # How frequent do we need to check? are 15s OK?
                time.sleep(15)
        except KeyboardInterrupt:
            log.warning("Stopped by user")
            break
        except Exception as err:
            log.debug("admins {}".format(config.get("admins", [])))
            message = "Erreur inattendue: veuillez consulter les logs.\n \u2023 {}".format(err)
            for admin in config.get("admins", []):
                kang.sim800.Sms(admin, message).send(sim)
            # We want to stay alive as much as possible, log errors and continue
            log.exception("Unexpected error")
            kang.sim800.Sms(sms.number, "Une erreur est survenue. Les adminstrateurs ont été notifiés.")

    scheduler_thread.stop()
    scheduler_thread.join()
    kang.relays.clean()
    sim.close()
    sys.exit(ret)

if __name__ == "__main__":
    main()
