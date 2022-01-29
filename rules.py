import GameData

def checkRules(s,playerName, data, hints):
    """
    Check the ruleSet, if a rule is satisfied, do the corresponding action
    s socket, playerName is the name of the agent playing the game,
    data are the data of the match, hints are the hints collected during the game 
    """

    # RULE 1: check if the player has a playable card -> action: play that card
    cardIdx = playableCard(playerName, data, hints)
    if(cardIdx != -1):
        print("\nMOVE: RULE 1 -> play a playable card")
        s.send(GameData.ClientPlayerPlayCardRequest(playerName, cardIdx).serialize())
        return

    # RULE 2: check if the player has a discardable card -> action: discard it
    cardIdx = discardableCard(playerName, data, hints)
    if(cardIdx != -1):
        print("\nMOVE: RULE 2 -> discard a discardable card")
        s.send(GameData.ClientPlayerDiscardCardRequest(
            playerName, cardIdx).serialize())
        return

    # RULE 3: check if another player has a playable card -> action: give hint
    player, hint_t, hint_v = otherPlayerPlayableCard(data, hints)
    if(player is not None):
        print("\nMOVE: RULE 3 -> hint playable card")
        s.send(GameData.ClientHintData(
            playerName, player, hint_t, hint_v).serialize())
        return

    # RULE 5: if note tokens were used -> action: discard oldest card, index = 0
    if data.usedNoteTokens > 0:
        print("\nMOVE: RULE 5 -> discard oldest card")
        s.send(GameData.ClientPlayerDiscardCardRequest(
            playerName, 0).serialize())
        return

    # RULE 6: default: -> play oldest card, index = 0
    print("\nMOVE: RULE 6 -> play oldest card")
    s.send(GameData.ClientPlayerPlayCardRequest(playerName, 0).serialize())
    return
    


def playableCard(playerName, data, hints):
    print("DBG - CHECK RULE 1")
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
            # Or If last added in the tableCard for that color has value - 1
            if ((value == 1 and len(data.tableCards[color]) == 0) or
                (len(data.tableCards[color]) > 0) and data.tableCards[color][-1].value == value - 1):
                valid_cards.append(idx)

    if len(valid_cards) > 0:
        # return the first index: TODO can be improved by checking if one of them is the last copy
        return valid_cards[0]
    return -1


def discardableCard(playerName, data, hints):
    print("DBG - CHECK RULE 2")
    """
    Check if there is a discardable card in the hand of the player with name = playerName
    A card is discardable if we have complete knowledge of that card, and can be u
    if yes: return card's index
    if no: return -1
    """
    # Cannot discard any cards because no Note tokens were used
    if data.usedNoteTokens == 0:
        return -1

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
            if (len(data.tableCards[color]) > 0) and data.tableCards[color][-1].value >= value:
                valid_cards.append(idx)
            # TODO: check if i have duplicate cards
            # TODO: check if in the discard pile there are all the cards for that color that block it
            # TODO: check if in the discard pile there are all the cards for that value that block it

        # Check for cards that we know only color
        elif (color != ""):
            # If the table is complete for that color
            if len(data.tableCards[color]) == 5:
                valid_cards.append(idx)

        # Check for cards that we know only value
        elif (value != 0):
            # Check if in all the table colors the number are already higher
            if ((len(data.tableCards["red"]) > value) and
                (len(data.tableCards["yellow"]) > value) and
                (len(data.tableCards["green"]) > value) and
                (len(data.tableCards["blue"]) > value) and
                    (len(data.tableCards["white"]) > value)):
                valid_cards.append(idx)

    if len(valid_cards) > 0:
        # return the first index: TODO can be improved by checking if one of them is the last copy
        return valid_cards[0]
    return -1


def otherPlayerPlayableCard(data, hints):
    print("DBG - CHECK RULE 3")
    """
    Check if another player has a playable card and find the best one, and the type of hint needed
    return the name of that player, and the hint type, and the hint value
    return None, None, None if no cards are playable
    """
    
    # Cannot give hints if all Note tokes were used
    if data.usedNoteTokens == 8:
        return None, None, None 


    best_card_idx = -1
    best_card_criticality = -1 # How many copies are left in the deck (or other player hands) 
    best_card_hint_completeness = -1 # If a hint would give complete knowledge to the player, hints already present on that card
    best_card_player = None
    best_card_hint_t = None
    best_card_hint_v = None

    for p in data.players:
        # we can see hands of other players, with complete info
        hand = p.hand 
        for idx, card in enumerate(hand):
            #color = card["color"]
            #value = card["value"]
            color = card.color
            value = card.value
            # Check if that card is playable
            # If it is a 1 and the pile is empty for that color
            # Or If last added in the tableCard for that color has value - 1
            if ((value == 1 and (len(data.tableCards[color]) == 0)) or
                (len(data.tableCards[color]) > 0) and data.tableCards[color][-1].value == value - 1):

                print("DBG: He has a playable card!!  idx = ", idx)

                # compare it with best so far

                # see criticality : how many copies are left for that card
                total = -1
                if value == 1:
                    total = 3
                elif value == 5:
                    total = 1
                else:
                    total = 2

                # see how many copies of that card are still in the deck (or in other hands)
                for c in data.discardPile:
                    if ((c.color == color) and (c.value == value)):
                        total -= 1
                criticality = total

                # see if it's the first hint, the second or two hints are already given
                # DBG: print(hints[p.name])
                hand_h = hints[p.name]
                hint_col = (hand_h[idx]["color"] == color)
                hint_val = (hand_h[idx]["value"] == value)
                completeness = 0
                if ((hint_col == True and hint_val == False) or (hint_col==False and hint_val == True)):
                    completeness = 1

                # if both hints are already given, look for other cards
                if (hint_col and hint_val):
                    pass
                else:
                    # first one, or this is more critical, or this hint gives a complete information and the saved one no
                    print("DBG: inside comparison")
                    if((best_card_idx == -1) or
                        (criticality < best_card_criticality) or
                        (completeness > best_card_hint_completeness)
                        ):
                        best_card_player = p.name
                        best_card_idx = idx
                        best_card_criticality = criticality
                        best_card_hint_completeness = completeness
                        # giving hint on color is better, if the hint is not already present
                        if hint_col:
                            best_card_hint_t = "value"
                            best_card_hint_v = value
                        else:
                            best_card_hint_t = "color"
                            best_card_hint_v = color


    return best_card_player, best_card_hint_t, best_card_hint_v

