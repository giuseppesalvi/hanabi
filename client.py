#!/usr/bin/env python3

from sys import argv, stdout
from telnetlib import NOP
from threading import Thread
import GameData
import socket
from constants import *
import os
import time


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
if playerName == "MANUAL":
    AGENT = False
started = False  # control the start of the game
myTurn = False  # control the turn of the agent


hints = {}
data_seen = None


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

    while run:
        if myTurn:
            # Play first card
            # print(playerName, ": PLAY FIRST CARD")
            # s.send(GameData.ClientPlayerPlayCardRequest(playerName, 0).serialize())

            # Check Rules and do corresponding action
            checkRules(playerName, data, hints)

            # End of my Turn
            myTurn = False
            time.sleep(3)

    # Game is finished, exit
    os._exit(0)


def checkRules(playerName, data, hints):

    # RULE 1: check if the player has a playable card -> action: play that card
    cardIdx = playableCard(playerName, data, hints)
    if(cardIdx != -1):
        s.send(GameData.ClientPlayerPlayCardRequest(playerName, 0).serialize())
        return

    # RULE 2: check if the player has a discardable card -> action: discard it
    cardIdx = discardableCard(playerName, data, hints)
    if(cardIdx != -1):
        s.send(GameData.ClientPlayerDiscardCardRequest(
            playerName, cardIdx).serialize())
        return
    
    # RULE 3: check if another player has a playable card -> action: give hint 


def playableCard(playerName, data, hints):
    """
    Check if there is a playable card in the hand of the player with name = playerName
    A card is playable if we have complete knowledge of that card, and can be used 
    if yes: return card's index
    if no: return -1
    """

    # list of indexes of valid cards
    valid_cards = []
    hand = hints[playerName]
    for idx, card in enumerate(hand):
        color = card["color"]
        value = card["value"]
        # Check if he has a card with all informations
        if (color != "" and value != 0):
            # Check if that card is playable
            # If it is a 1 and the pile is empty for that color
            if value == 1 and len(data.tableCards[color] == 0):
                valid_cards.append(idx)
            # If last added in the tableCard for that color has value - 1
            if len(data.tableCards[color] > 0) and data.tableCards[color][-1].value == value - 1:
                valid_cards.append(idx)

    if len(valid_cards > 0):
        # return the first index: TODO can be improved by checking if one of them is the last copy
        return valid_cards[0]
    return -1


def discardableCard(playerName, data, hints):
    """
    Check if there is a discardable card in the hand of the player with name = playerName
    A card is discardable if we have complete knowledge of that card, and can be u
    if yes: return card's index
    if no: return -1
    """

    # list of indexes of valid cards
    valid_cards = []
    hand = hints[playerName]
    for idx, card in enumerate(hand):
        color = card["color"]
        value = card["value"]
        # Check if that card discardable
        # Check if he has a card with all informations
        if (color != "" and value != 0):
            # If the table has higher or equal value for that color
            if (len(data.tableCards[color] > 0) and data.tableCards[color][-1].value >= value):
                valid_cards.append(idx)
            # TODO: check if i have duplicate cards
            # TODO: check if in the discard pile there are all the cards for that color that block it
            # TODO: check if in the discard pile there are all the cards for that value that block it

        # Check for cards that we know only color
        elif (color != ""):
            # If the table is complete for that color
            if len(data.tableCards[color] == 5):
                valid_cards.append(idx)

        # Check for cards that we know only value
        elif (value != 0):
            # Check if in all the table colors the number are already higher
            if (len(data.tableCards["red"] > value) and
                (len(data.tableCards["yellow"]) > value) and
                (len(data.tableCards["green"]) > value) and
                (len(data.tableCards["blue"]) > value) and
                    (len(data.tableCards["white"]) > value)):
                valid_cards.append(idx)

    if len(valid_cards > 0):
        # return the first index: TODO can be improved by checking if one of them is the last copy
        return valid_cards[0]
    return -1


def manageInput():
    global run
    global status
    while run:
        command = input()
        # Choose data to send
        if command == "exit":
            run = False
            os._exit(0)
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

            # GAME CAN START INITIALIZE INFORMATIONS !!!

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
                # ADD INFO ABOUT HANDS TO LOCAL VARIABLES
                #                for player in data.players:
                # for i, card in enumerate(player.hand):
                #hands[player][i]["color"] = card.color
                #hands[player][i]["value"] = card.value
                # print("PPPPPPPP")
                # print(hands)

                data_seen = data
                myTurn = True
            else:
                myTurn = False

        if type(data) is GameData.ServerActionInvalid:
            dataOk = True
            print("Invalid action performed. Reason:")
            print(data.message)
        if type(data) is GameData.ServerActionValid:
            dataOk = True
            print("Action valid!")
            print("Current player: " + data.player)

            next_turn()

        if type(data) is GameData.ServerPlayerMoveOk:
            dataOk = True
            print("Nice move!")
            print("Current player: " + data.player)

            next_turn()
        if type(data) is GameData.ServerPlayerThunderStrike:
            dataOk = True
            print("OH NO! The Gods are unhappy with you!")

            next_turn()

        if type(data) is GameData.ServerHintData:
            dataOk = True
            print("Hint type: " + data.type)
            print("Player " + data.destination +
                  " cards with value " + str(data.value) + " are:")
            for i in data.positions:
                print("\t" + str(i))
            next_turn()

        if type(data) is GameData.ServerInvalidDataReceived:
            dataOk = True
            print(data.data)
        if type(data) is GameData.ServerGameOver:
            dataOk = True
            print(data.message)
            print(data.score)
            print(data.scoreMessage)
            stdout.flush()
            run = False  # run = False   COMMENT IF WANT TO PLAY MORE THAN ONE
            print("Ready for a new game!")
        if not dataOk:
            print("Unknown or unimplemented data type: " + str(type(data)))
        print("[" + playerName + " - " + status + "]: ", end="")
        stdout.flush()
