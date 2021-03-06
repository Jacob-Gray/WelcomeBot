#!/usr/bin/env python
from excepthook import uncaught_exception, install_thread_excepthook
import sys
sys.excepthook = uncaught_exception
install_thread_excepthook()

import getpass
import logging
import logging.handlers
import os
import time
import shelve
import random
import re
import requests
from threading import Thread

import ChatExchange.chatexchange.client
import ChatExchange.chatexchange.events
import ChatExchange.chatexchange.browser
import who_to_welcome
import image_search
import weather_search
import youtube_search
import google_search
from BotProperties import BotProperties

logger = logging.getLogger(__name__)

host_id = ''
room_id = 0
bot = None
room = None


def main():
    global host_id
    global room_id
    global bot
    global room

    setup_logging()
    # Run `. setp.sh` to set the below testing environment variables

    def welcome_bot_host_options():
        print "Welcome Bot Host Site Options (select 1, 2, or 3)"
        print "  1. chat.stackexchange.com"
        print "  2. chat.meta.stackexchange.com"
        print "  3. chat.stackoverflow.com"
        print "What will be your Welcome Bot's host site?"
    if 'HostSite' in os.environ:
        host_id_choice = os.environ['HostSite']
        if host_id_choice == '1':
            print "You have chosen chat.stackexchange.com as your Welcome Bot's host site."
            host_id = 'stackexchange.com'
        elif host_id_choice == '2':
            print "You have chosen meta.chat.stackexchange.com as your Welcome Bot's host site."
            host_id = 'meta.stackexchange.com'
        elif host_id_choice == '3':
            print "You have chosen chat.stackoverflow.com as your Welcome Bot's host site."
            host_id = 'stackoverflow.com'
    else:
        welcome_bot_host_options()
        host_id_choice = raw_input()
        while host_id_choice not in ['1', '2', '3']:
            print "Invalid Choice"
            welcome_bot_host_options()
            host_id_choice = raw_input()
        if host_id_choice == '1':
            print "You have chosen chat.stackexchange.com as your Welcome Bot's host site."
            host_id = 'stackexchange.com'
        elif host_id_choice == '2':
            print "You have chosen meta.chat.stackexchange.com as your Welcome Bot's host site."
            host_id = 'meta.stackexchange.com'
        elif host_id_choice == '3':
            print "You have chosen chat.stackoverflow.com as your Welcome Bot's host site."
            host_id = 'stackoverflow.com'

    if 'RoomID' in os.environ:
        room_id = os.environ['RoomID']
    else:
        print "What is the room's ID?"
        room_id_choice = raw_input()
        while not room_id_choice.isdigit():
            print "Invalid Input, must be a number"
            room_id_choice = raw_input()
        room_id = room_id_choice

    if 'WelcomeMessage' in os.environ:
        BotProperties.welcome_message = os.environ['WelcomeMessage']
    else:
        print "What would you like the welcome message to be?"
        BotProperties.welcome_message = raw_input()

    if 'ChatExchangeU' in os.environ:
        email = os.environ['ChatExchangeU']
    else:
        email = raw_input("Email: ")
    if 'ChatExchangeP' in os.environ:
        password = os.environ['ChatExchangeP']
    else:
        password = getpass.getpass("Password: ")

    client = ChatExchange.chatexchange.client.Client(host_id)
    client.login(email, password)

    bot = client.get_me()

    room = client.get_room(room_id)
    room.join()
    room.watch(on_event)

    print "(You are now in room #%s on %s.)" % (room_id, host_id)
    if "first_start" in sys.argv:
        room.send_message("I'm alive :) (running on commit: " + os.popen('git log --pretty=format:"%h" -n 1').read() + ")")

    while True:
        message = raw_input("<< ")
        if message == "die":
            room.send_message("I'm dead :(")
            time.sleep(0.4)
            break
        else:
            room.send_message(message)

    os._exit(6)


def on_event(event, client):
    if not BotProperties.paused:
        if isinstance(event, ChatExchange.chatexchange.events.UserEntered):
            on_enter(event)
        elif isinstance(event, ChatExchange.chatexchange.events.MessagePosted):
            on_command(event, client)
    else:
        priv_users = shelve.open("privileged_users.txt")
        if isinstance(event, ChatExchange.chatexchange.events.MessagePosted) and event.content.startswith(":start"):
            if (event.user.id == 121401 and host_id == 'stackexchange.com') or (event.user.id == 284141 and host_id == 'meta.stackexchange.com') or (event.user.id == 4087357 and host_id == 'stackoverflow.com') or (str(event.user.id) in priv_users[host_id + room_id]):
                BotProperties.paused = False
                event.message.reply("I am now resuming :)")
        priv_users.close()


def on_enter(event):
    print "User Entered"
    if len(BotProperties.welcome_message) < 1:
        pass
    else:
        if event.user.id == bot.id or event.user.reputation < 20:
            pass
        else:
            if who_to_welcome.check_user(event.user.id, room_id, 'enter'):
                room.send_message("@" + event.user.name.replace(" ", "") + " " + BotProperties.welcome_message)


def on_command(message, client):
    priv_users = shelve.open("privileged_users.txt")
    print "Message Posted"
    message.content = chaterize_message(message.content)

    if message.content.startswith(":image"):
        print "Is image request"
        if len(message.content.split()) == 1:
            message.message.reply("No search term given")
        else:
            def perform_image_search():
                search_term = "+".join(message.content.split()[1:])
                image = image_search.search_image(search_term)
                print image
                if image is False:
                    print "No Image"
                    message.message.reply("No image was found for " + message.content[8:])
                else:
                    print message.content
                    print search_term
                    message.message.reply(image)
            t = Thread(target=perform_image_search)
            t.start()
    elif message.content.startswith(":alive"):
        print "Is alive request"
        message.message.reply("Indeed :D")

    elif message.content.startswith(":testenter"):
        print "Is testenter request"
        room.send_message("@SkynetTestUser " + BotProperties.welcome_message)

    elif message.content.startswith(":search"):
        print "Is search request"
        if len(message.content.split()) == 1:
            message.message.reply("Can't search, no terms given")
        else:
            def perform_google_search():
                search_term = "+".join(message.content.split()[1:])
                try:
                    results, moreResultsUrl = google_search.google_search(search_term)
                    print results
                except TypeError:
                    print "No results"
                    message.message.reply("No results were found for " + message.content[9:])
                    return

                print message.content
                print search_term

                message.message.reply("Search results for **%s**: " % message.content[9:])

                # sould be configurable
                count = len(results) < 3 and len(results) or 3
                for i in range(0, count):
                    res = results[i]
                    room.send_message("[%s](%s)" % (res['titleNoFormatting'], res['unescapedUrl']))
                    room.send_message(chaterize_message(res["content"]).replace("\n", " "))

                room.send_message("[See More...](%s)" % moreResultsUrl)

            g = Thread(target=perform_google_search)
            g.start()

    elif message.content.startswith(":info"):
        print "Is info request"
        message.message.reply("Host ID: " + host_id + "\nRoom ID: " + room_id + "\nWelcome Message:\n" + BotProperties.welcome_message)

    elif message.content.startswith(":editmsg"):
        print "Is message edit request"
        if (message.user.id == 121401 and host_id == 'stackexchange.com') or (message.user.id == 284141 and host_id == 'meta.stackexchange.com') or (message.user.id == 4087357 and host_id == 'stackoverflow.com') or (str(message.user.id) in priv_users[host_id + room_id]):
            if len(message.content.split()) == 1:
                message.message.reply("No string given")
            else:
                u_welcome_message = " ".join(message.content.split()[1:])
                print u_welcome_message
                if '</a>' in u_welcome_message:
                    print "is link"
                    text_before = u_welcome_message[:u_welcome_message.find('<a href')]
                    text_after = u_welcome_message[(u_welcome_message.find('</a>') + 4):]
                    link_opening = u_welcome_message.find('href="') + 6
                    link_ending = u_welcome_message.find('" rel=')
                    link = u_welcome_message[link_opening:link_ending]
                    text_opening = u_welcome_message.find('ow">') + 4
                    text_ending = u_welcome_message.find('</a>')
                    link_text = u_welcome_message[text_opening:text_ending]
                    BotProperties.welcome_message = text_before + "[" + link_text + "](" + link + ")" + text_after
                else:
                    BotProperties.welcome_message = u_welcome_message
                message.message.reply("Welcome message changed to: " + BotProperties.welcome_message)
        else:
            message.message.reply("You are not authorized to edit the welcome message. Please contact michaelpri if it needs to be changed.")

    elif message.content.startswith(":die"):
        if (message.user.id == 121401 and host_id == 'stackexchange.com') or (message.user.id == 284141 and host_id == 'meta.stackexchange.com') or (message.user.id == 4087357 and host_id == 'stackoverflow.com') or (str(message.user.id) in priv_users[host_id + room_id]):
            message.message.reply("I'm dead :(")
            time.sleep(0.4)
            os._exit(6)
        else:
            message.message.reply("You are not authorized kill me!!! Muahaha!!!! Please contact michaelpri if I am acting up.")
    elif message.content.startswith(":reset"):
        if (message.user.id == 121401 and host_id == 'stackexchange.com') or (message.user.id == 284141 and host_id == 'meta.stackexchange.com') or (message.user.id == 4087357 and host_id == 'stackoverflow.com') or (str(message.user.id) in priv_users[host_id + room_id]):
            message.message.reply("Resetting...")
            time.sleep(0.4)
            os._exit(5)
        else:
            message.message.reply("You are not authorized reset me. Please contatct michaelpri if I need resetting.")
    elif message.content.startswith(":source"):
        message.message.reply("My source code can be found on [GitHub](https://github.com/michaelpri10/WelcomeBot)")
    elif message.content.startswith(":pull"):
        if (message.user.id == 121401 and host_id == 'stackexchange.com') or (message.user.id == 284141 and host_id == 'meta.stackexchange.com') or (message.user.id == 4087357 and host_id == 'stackoverflow.com') or (str(message.user.id) in priv_users[host_id + room_id]):
            os._exit(3)
        else:
            message.message.reply("You are not authorized to pull. Please contatct michaelpri if I need some pulling.")

    elif message.content.startswith(":priv"):
        if (message.user.id == 121401 and host_id == 'stackexchange.com') or (message.user.id == 284141 and host_id == 'meta.stackexchange.com') or (message.user.id == 4087357 and host_id == 'stackoverflow.com') or (str(message.user.id) in priv_users[host_id + room_id]):
            if len(message.content.split()) == 2:
                user_to_priv = message.content.split()[1]
                if (host_id + room_id) not in priv_users:
                    priv_users[host_id + room_id] = []
                if user_to_priv in priv_users[host_id + room_id]:
                    message.message.reply("User already privileged")
                else:
                    priv_users[host_id + room_id] += [user_to_priv]
                    message.message.reply("User " + user_to_priv + " added to privileged users for room " + room_id + " on chat." + host_id)
            else:
                message.message.reply("Invalid privilege giving")
        else:
            message.message.reply("You are not authorized to add privileged users :( Please contact michaelpri if someone needs privileges.")
    elif message.content.startswith(":choose"):
        print "Is choose request"
        if len(message.content.split()) == 1:
            message.message.reply("No choices given")
        else:
            if " or " in message.content:
                choices = message.content[8:].split(" or ")
                message.message.reply("I choose " + random.choice(choices))
            else:
                message.message.reply("I'm not sure what your options are")
    elif message.content.startswith(":help"):
        print "Is help request"
        message.message.reply("""My Commands
                                 - //image (search term)
                                 - //choose (choice) or (choice) [or choice...]
                                 - //weather (city)[, country/state]
                                 - //youtube (search term)
                                 - //source
                                 - //info
                                 - //search (search term)
                            """)
        if (message.user.id == 121401 and host_id == 'stackexchange.com') or (message.user.id == 284141 and host_id == 'meta.stackexchange.com') or (message.user.id == 4087357 and host_id == 'stackoverflow.com') or (str(message.user.id) in priv_users[host_id + room_id]):
            message.message.reply("""You are a privileged user, so you can also use these commands:
                                     - //pull
                                     - //pause
                                     - //start
                                     - //die
                                     - //priv
                                     - //reset
                                     - //editmsg [new welcome message]
                                """)
    elif message.content.startswith(":weather"):
        print "Is weather request"
        if len(message.content.split()) == 1:
            message.message.reply("City and country/state not given")
        else:
            def perform_weather_search():
                city_and_country = [i.replace(" ", "%20") for i in message.content[10:].split(",")]
                city = city_and_country[0]
                if len(city_and_country) == 2:
                    country_state = city_and_country[1]
                    print city, country_state
                    try:
                        message.message.reply(weather_search.weather_search(city, country_state))
                    except:
                        message.message.reply("Couldn't find weather info for " + message.content)
                elif len(city_and_country) == 1:
                    try:
                        message.message.reply(weather_search.weather_search(city, ""))
                    except:
                        message.message.reply("Couldn't find weather info for " + message.content)
            w = Thread(target=perform_weather_search)
            w.start()
    elif message.content.startswith(":youtube"):
        print "Is youtube request"
        if len(message.content.split()) == 1:
            message.message.reply("No search term given")
        else:
            def perform_youtube_search():
                search_term = "+".join(message.content.split()[1:])
                video = youtube_search.youtube_search(search_term)
                print video
                if video is False:
                    print "No Image"
                    message.message.reply("No video was found for " + search_term)
                else:
                    print message.content
                    print search_term
                    message.message.reply(video)
            v = Thread(target=perform_youtube_search)
            v.start()
    elif message.content.startswith(":pause"):
        if (message.user.id == 121401 and host_id == 'stackexchange.com') or (message.user.id == 284141 and host_id == 'meta.stackexchange.com') or (message.user.id == 4087357 and host_id == 'stackoverflow.com') or (str(message.user.id) in priv_users[host_id + room_id]):
            BotProperties.paused = True
            message.message.reply("I am now paused :|")
        else:
            message.message.reply("You are not authorized to pause me. Please contact michaelpri if I need some pausing.")
    elif re.compile("^:[0-9]+ delete$").search(message.message.content_source):
        if (message.user.id == 121401 and host_id == 'stackexchange.com') or (message.user.id == 284141 and host_id == 'meta.stackexchange.com') or (message.user.id == 4087357 and host_id == 'stackoverflow.com') or (str(message.user.id) in priv_users[host_id + room_id]):
            message_to_delete = client.get_message(int(message.message.content_source.split(" ")[0][1:]))
            try:
                message_to_delete.delete()
            except requests.HTTPError:
                pass
        else:
            message.message.reply("You are not authorized to delete one of my messages.")

    priv_users.close()


def chaterize_message(message):

    message = message.replace('&quot;', '"')
    message = message.replace("&#39;", "'")
    message = message.replace("</i>", "*")
    message = message.replace("<i>", "*")
    message = message.replace("</b>", "**")
    message = message.replace("<b>", "**")
    message = message.replace("</i></b>", "***")
    message = message.replace("<b><i>", "***")
    return message


def setup_logging():
    logging.basicConfig(level=logging.INFO)
    logger.setLevel(logging.DEBUG)

    # In addition to the basic stderr logging configured globally
    # above, we'll use a log file for chatexchange.client.
    wrapper_logger = logging.getLogger('ChatExchange.chatexchange.client')
    wrapper_handler = logging.handlers.TimedRotatingFileHandler(
        filename='client.log',
        when='midnight', delay=True, utc=True, backupCount=7,
    )
    wrapper_handler.setFormatter(logging.Formatter(
        "%(asctime)s: %(levelname)s: %(threadName)s: %(message)s"
    ))
    wrapper_logger.addHandler(wrapper_handler)

if __name__ == '__main__':
    main()
