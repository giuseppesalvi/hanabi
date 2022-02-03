#!/usr/bin/env python3

from sys import argv, stdout
from telnetlib import NOP
from threading import Thread
import GameData
import socket
from constants import *
import os
from rules import checkRules
import time
from copy import deepcopy
import stats


if len(argv) < 4:
    print("You need the player name to start the game.")
    # exit(-1)
    playerName = "Test"  # For debug
    ip = HOST
    port = PORT
else:
    playerName = argv[3]
    ip = argv[1]
    port = int(argv[2])

run = True

statuses = ["Lobby", "Game", "GameHint"]

status = statuses[0]

hintState = ("", "")

AGENT = True
if playerName == "MANUAL" or playerName == "manual":
    AGENT = False
started = False  # control the start of the game
myTurn = False  # control the turn of the agent


hints = {}
data_seen = None  # contains the state of the game

NUM_MATCHES = 100
scores = []


def agent():
    global run
    global status
    global started
    global myTurn

    # Initialize the agent
    # I'm ready ...
    s.send(GameData.ClientPlayerStartRequest(playerName).serialize())

    while not started:
        pass

    while run and len(scores) < NUM_MATCHES:
        if myTurn:

            if not data_seen:
                continue

            # Check Rules and do corresponding action
            checkRules(s, playerName, data_seen, hints)

            # End of my Turn
            myTurn = False

    print("RULES USED")
    print(stats.rules_used)
    print("LOST GAMES")
    print(stats.lost_games)
    # Game(s) finished, exit
    os._exit(0)


def manageInput():
    global run
    global status
    while run:
        command = input()
        # Choose data to send
        if command == "exit":
            run = False
            os._exit(0)
        # DBG
        elif command == "hints" and status == statuses[1]:
            print("HINTS SO FAR")
            print(hints)
        elif command == "ready" and status == statuses[0]:
            s.send(GameData.ClientPlayerStartRequest(playerName).serialize())
        elif command == "show" and status == statuses[1]:
            s.send(GameData.ClientGetGameStateRequest(playerName).serialize())
        elif command.split(" ")[0] == "discard" and status == statuses[1]:
            try:
                cardStr = command.split(" ")
                cardOrder = int(cardStr[1])
                s.send(GameData.ClientPlayerDiscardCardRequest(
                    playerName, cardOrder).serialize())
            except:
                print("Maybe you wanted to type 'discard <num>'?")
                continue
        elif command.split(" ")[0] == "play" and status == statuses[1]:
            try:
                cardStr = command.split(" ")
                cardOrder = int(cardStr[1])
                s.send(GameData.ClientPlayerPlayCardRequest(
                    playerName, cardOrder).serialize())
            except:
                print("Maybe you wanted to type 'play <num>'?")
                continue
        elif command.split(" ")[0] == "hint" and status == statuses[1]:
            try:
                destination = command.split(" ")[2]
                t = command.split(" ")[1].lower()
                if t != "colour" and t != "color" and t != "value":
                    print("Error: type can be 'color' or 'value'")
                    continue
                value = command.split(" ")[3].lower()
                if t == "value":
                    value = int(value)
                    if int(value) > 5 or int(value) < 1:
                        print("Error: card values can range from 1 to 5")
                        continue
                else:
                    if value not in ["green", "red", "blue", "yellow", "white"]:
                        print(
                            "Error: card color can only be green, red, blue, yellow or white")
                        continue
                s.send(GameData.ClientHintData(
                    playerName, destination, t, value).serialize())
            except:
                print("Maybe you wanted to type 'hint <type> <destinatary> <value>'?")
                continue
        elif command == "":
            print("[" + playerName + " - " + status + "]: ", end="")
        else:
            print("Unknown command: " + command)
            continue
        stdout.flush()


def next_turn():
    # next turn: get game state from the server
    s.send(GameData.ClientGetGameStateRequest(playerName).serialize())


with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    request = GameData.ClientPlayerAddData(playerName)
    s.connect((HOST, PORT))
    s.send(request.serialize())
    data = s.recv(DATASIZE)
    data = GameData.GameData.deserialize(data)
    if type(data) is GameData.ServerPlayerConnectionOk:
        print("Connection accepted by the server. Welcome " + playerName)
    print("[" + playerName + " - " + status + "]: ", end="")
    if AGENT:
        Thread(target=agent).start()
    else:
        Thread(target=manageInput).start()
    while run:
        dataOk = False
        data = s.recv(DATASIZE)
        if not data:
            continue
        data = GameData.GameData.deserialize(data)
        if type(data) is GameData.ServerPlayerStartRequestAccepted:
            dataOk = True
            print("Ready: " + str(data.acceptedStartRequests) +
                  "/" + str(data.connectedPlayers) + " players")
            data = s.recv(DATASIZE)
            data = GameData.GameData.deserialize(data)
        if type(data) is GameData.ServerStartGameData:
            dataOk = True
            print("Game start!")
            s.send(GameData.ClientPlayerReadyData(playerName).serialize())
            status = statuses[1]

            # Initialize hints knowing the number of players
            # 4 or 5 players: 4 cards, 2 or 3 players : 5 cards
            num_cards = 4 if len(data.players) > 3 else 5
            for p in data.players:
                l = []
                for c in range(num_cards):
                    l.append({"color": "", "value": 0})
                hints[p] = l

            started = True
            next_turn()
        if type(data) is GameData.ServerGameStateData:
            dataOk = True
            print("\n\nCurrent player: " + data.currentPlayer)
            print("Player hands: ")
            for p in data.players:
                print(p.toClientString())
            print("Cards in your hand: " + str(data.handSize))
            print("Table cards: ")
            for pos in data.tableCards:
                print(pos + ": [ ")
                for c in data.tableCards[pos]:
                    print(c.toClientString() + " ")
                print("]")
            print("Discard pile: ")
            for c in data.discardPile:
                print("\t" + c.toClientString())
            print("Note tokens used: " + str(data.usedNoteTokens) + "/8")
            print("Storm tokens used: " + str(data.usedStormTokens) + "/3\n\n")

            # check if it's this player's turn
            if data.currentPlayer == playerName:
                data_seen = deepcopy(data)

                myTurn = True
            else:
                myTurn = False

        if type(data) is GameData.ServerActionInvalid:
            dataOk = True
            print("Invalid action performed. Reason:")
            print(data.message)

            next_turn()

        if type(data) is GameData.ServerActionValid:
            # DISCARDED CARDS
            dataOk = True
            print("Action valid!")
            print("Current player: " + data.player)

            last_player = data.lastPlayer
            last_card_played_idx = data.cardHandIndex

            hints[last_player].pop(last_card_played_idx)
            hints[last_player].append({"color": "", "value": 0})

            next_turn()

        if type(data) is GameData.ServerPlayerMoveOk:
            # PLAYED CARDS
            dataOk = True
            print("Nice move!")
            print("Current player: " + data.player)

            last_player = data.lastPlayer
            last_card_played_idx = data.cardHandIndex

            hints[last_player].pop(last_card_played_idx)
            hints[last_player].append({"color": "", "value": 0})

            next_turn()

        if type(data) is GameData.ServerPlayerThunderStrike:
            # PLAYED WRONG CARDS
            dataOk = True
            print("OH NO! The Gods are unhappy with you!")

            last_player = data.lastPlayer
            last_card_played_idx = data.cardHandIndex

            hints[last_player].pop(last_card_played_idx)
            hints[last_player].append({"color": "", "value": 0})

            next_turn()

        if type(data) is GameData.ServerHintData:
            dataOk = True
            print("Hint type: " + data.type)
            print("Player " + data.destination +
                  " cards with value " + str(data.value) + " are:")
            for i in data.positions:
                print("\t" + str(i))

                hints[data.destination][i][data.type] = data.value

            next_turn()

        if type(data) is GameData.ServerInvalidDataReceived:
            dataOk = True
            print(data.data)

            next_turn()
        if type(data) is GameData.ServerGameOver:
            dataOk = True
            print(data.message)
            print(data.score)
            print(data.scoreMessage)
            stdout.flush()

            #run = False
            if data.score == 0:
                stats.lost_games += 1

            scores.append(data.score)

            print("\nMATCHES PLAYED = ", len(scores), "/", NUM_MATCHES)
            print("AVG SCORE = %.2f" % (sum(scores) / len(scores)), "\n")

            print("Ready for a new game!")

            # Restart the game

            # Restore the hints
            hints = {}
            num_cards = 4 if len(data_seen.players) > 3 else 5
            for p in data_seen.players:
                l = []
                for c in range(num_cards):
                    l.append({"color": "", "value": 0})
                hints[p.name] = l
            data_seen = None

            time.sleep(1)
            next_turn()

        if not dataOk:
            print("Unknown or unimplemented data type: " + str(type(data)))
