import GameData
import globals

DBG = False

RULE3VERSION = 1
RULE5COMPLETEONLY = True
RULE6VERSION = 1 
RULE9VERSION = 2

def checkRules(s, playerName, data, hints):
    """
    Check the ruleSet, if a rule is satisfied, do the corresponding action
    s socket, playerName is the name of the agent playing the game,
    data are the data of the match, hints are the hints collected during the game 
    """

    global RULE3VERSION
    global RULE5COMPLETEONLY
    global RULE6VERSION
    global RULE9VERSION

    # Conservative Approach: "play a card only if if you are sure that is playable or no other moves are possible,
    # in order to avoid loosing matches with 3 red strikes"

    # Select which rules to apply and their order
    rule_set = [rule_1, rule_2, rule_3, rule_4, rule_5, rule_6, rule_7, rule_8]
    #rule_set = [rule_1, rule_2, rule_3, rule_4, rule_5, rule_6, rule_9, rule_7, rule_8]

    # Choose versions for some of the rules
    RULE3VERSION = 1
    RULE5COMPLETEONLY = True
    RULE6VERSION = 1  

    RULE9VERSION = 1

    for rule in rule_set:
        # go throught the rules in the order of the rule_set
        # when the first rule is satisfied, it performs the action and returns true
        if rule(s, playerName, data, hints):
            return 


def rule_1(s, playerName, data, hints):
    """
    RULE 1: check if the player has a playable card -> action: play it
    """
    cardIdx = playableCard(playerName, data, hints)
    if(cardIdx != -1):
        print("\nMOVE: RULE 1 -> play a playable card")
        s.send(GameData.ClientPlayerPlayCardRequest(
            playerName, cardIdx).serialize())
        globals.rules_used[0] += 1
        return True
    return False


def rule_2(s, playerName, data, hints):
    """
    RULE 2: check if the player has a discardable card -> action: discard it
    """
    cardIdx = discardableCard(playerName, data, hints)
    if(cardIdx != -1):
        print("\nMOVE: RULE 2 -> discard a discardable card")
        s.send(GameData.ClientPlayerDiscardCardRequest(
            playerName, cardIdx).serialize())
        globals.rules_used[1] += 1
        return True
    return False


def rule_3(s, playerName, data, hints):
    """
    RULE 3: check if another player has a playable card -> action: give hint
    """
    player, hint_t, hint_v = otherPlayerPlayableCard(playerName, data, hints, version=RULE3VERSION)
    if(player is not None):
        print("\nMOVE: RULE 3 -> hint playable card")
        s.send(GameData.ClientHintData(
            playerName, player, hint_t, hint_v).serialize())
        globals.rules_used[2] += 1
        return True
    return False


def rule_4(s, playerName, data, hints):
    """
    RULE 4 : other player has critical card in first position -> action: give hint
    """
    player, hint_t, hint_v = otherPlayerCriticalCardFirstPosition(
        playerName, data, hints)
    if(player is not None):
        print("\nMOVE: RULE 4 -> hint critical")
        s.send(GameData.ClientHintData(
            playerName, player, hint_t, hint_v).serialize())
        globals.rules_used[3] += 1
        return True
    return False


def rule_5(s, playerName, data, hints):
    """
    RULE 5 : other player has a discardable card -> action: give hint
    """
    player, hint_t, hint_v = otherPlayerDiscardableCard(
        playerName, data, hints, onlyComplete=RULE5COMPLETEONLY)
    if player is not None:
        print("\nMOVE: RULE 5a -> hint discardable card")
        s.send(GameData.ClientHintData(
            playerName, player, hint_t, hint_v).serialize())
        globals.rules_used[4] += 1
        return True
    return False


def rule_6(s, playerName, data, hints):
    """
    RULE 6: no playable cards but note tokens available -> action: give hint that gives more info
    """
    if data.usedNoteTokens < 8:
        print("\nMOVE: RULE 6 -> hint with more informations")
        player, hint_t, hint_v = hintWithMoreInfo(
            playerName, data, hints, version=RULE6VERSION)
        s.send(GameData.ClientHintData(
            playerName, player, hint_t, hint_v).serialize())
        globals.rules_used[5] += 1
        return True
    return False

def rule_9(s, playerName, data, hints):
    """
    RULE 9: if no risk of loosing the game and possible good playable card -> action: risky play 
    """
    cardIdx = riskyPlayableCard(playerName, data, hints, version = RULE9VERSION)
    if cardIdx != -1:
        print("\nMOVE: RULE 9 -> risky play")
        s.send(GameData.ClientPlayerPlayCardRequest(
            playerName, cardIdx).serialize())
        globals.rules_used[8] += 1
    return False

def rule_7(s, playerName, data, hints):
    """
    RULE 7: if note tokens were used -> action: discard oldest card with no hints
    """
    cardIdx = discardOldestWithNoHints(playerName, data, hints)
    if(cardIdx != -1):
        print("\nMOVE: RULE 7 -> discard oldest card with no hints")
        s.send(GameData.ClientPlayerDiscardCardRequest(
            playerName, cardIdx).serialize())
        globals.rules_used[6] += 1
        return True
    return False


def rule_8(s, playerName, data, hints):
    """
    RULE 8: default: risky play -> play oldest card, index = 0
    """
    print("\nMOVE: RULE 8 -> play oldest card")
    s.send(GameData.ClientPlayerPlayCardRequest(playerName, 0).serialize())
    globals.rules_used[7] += 1
    return True


def isPlayable(table, color, value):
    """
    Check if a card is playable given the table, the color of the card and the value of the card
    """
    return value == len(table[color]) + 1

def noCopiesLeftInDeckOrHand(playerName, data, color, value):
    """
    Return True if no copies are left of the card with value and color in the deck or in the player's hand,
    this means that all the copies are in the discardTable or in other players hands, or already in the table
    """

    total = -1
    if value == 1:
        total = 3
    elif value == 5:
        total = 1
    else:
        total = 2
    
    # subtract the copies found in the discard pile
    for c in data.discardPile:
        if c.color == color and c.value == value:
            total -= 1
    # subtract the copies in other players hands
    for p in data.players:
        # skip myself
        if p.name == playerName:
            continue
        h = p.hand
        for c in h:
            if c.color == color and c.value == value:
                total -= 1
    # if the card is already in the table, subtract 1
    if len(data.tableCards[color]) >= value:
        total -= 1 
            
    return total == 0


def playableCard(playerName, data, hints):
    """
    Check if there is a playable card in the hand of the player with name = playerName
    A card is playable if we have complete knowledge of that card, and can be used 
    if yes: return card's index
    if no: return -1
    """

    if DBG:
        print("DBG - CHECK RULE 1")

    hand = hints[playerName]
    for idx, card in enumerate(hand):
        color = card["color"]
        value = card["value"]

        # Check if he has a card with all informations
        if (color != "" and value != 0):
            # Check if that card is playable
            if isPlayable(data.tableCards, color, value):
                return idx 
        
        # Let's see if we don't have complete information through hints, but we can achieve it 
        # looking at the DiscardPile and other player's hands

        # if we know the color
        elif color != "":
            # see if all the values for that color are not in deck or my hand except one
            tot = 0
            for v in [1,2,3,4,5] :
                if not noCopiesLeftInDeckOrHand(playerName, data, color, v):
                # if for that value and color there are still copies, +1
                    tot += 1
            
            # for that color, there are copies of only one value
            if tot == 1:
                for v in [1,2,3,4,5] :
                    if not noCopiesLeftInDeckOrHand(playerName, data, color, v):
                        # it's the only one which has copies left
                        if isPlayable(data.tableCards,color, v):
                            return idx
 
        # if we know only the value
        elif value != 0:
            # see if all cards with that value left could be played. ex: first move all ones can be used
            if ((noCopiesLeftInDeckOrHand(playerName, data, "red", value) or isPlayable(data.tableCards, "red", value) )and 
                (noCopiesLeftInDeckOrHand(playerName, data, "yellow", value) or isPlayable(data.tableCards, "yellow", value)) and
                (noCopiesLeftInDeckOrHand(playerName, data, "green", value) or isPlayable(data.tableCards, "green", value)) and
                (noCopiesLeftInDeckOrHand(playerName, data, "blue", value) or isPlayable(data.tableCards, "blue", value) )and
                (noCopiesLeftInDeckOrHand(playerName, data, "white", value) or isPlayable(data.tableCards, "white", value))):
                return idx

    return -1


def discardableCard(playerName, data, hints):
    """
    Check if there is a discardable card in the hand of the player with name = playerName
    A card is discardable if we have complete knowledge of that card, and can be discarded 
    if yes: return card's index
    if no: return -1
    """

    if DBG:
        print("DBG - CHECK RULE 2")

    # Cannot discard any cards because no Note tokens were used
    if data.usedNoteTokens == 0:
        return -1

    hand = hints[playerName]
    for idx, card in enumerate(hand):
        color = card["color"]
        value = card["value"]
        # Check if that card is discardable
        # Check if he has a card with all informations
        if (color != "" and value != 0):
            # If the table has higher or equal value for that color
            if (len(data.tableCards[color]) > 0) and data.tableCards[color][-1].value >= value:
                return idx

            # check if i have duplicate cards
            for j, c in enumerate(hand):
                if j != idx and c["color"] == color and c["value"] == value:
                    return idx

        # Check for cards that we know the color
        if (color != ""):
            # If the table is complete for that color
            if len(data.tableCards[color]) == 5:
                return idx
            
            # If the table for that color is blocked, because no copies of the next card are left
            next_val = len(data.tableCards[color])
            # count how many copies for that card are left
            total = -1
            if next_val == 1:
                total = 3
            elif next_val == 5:
                total = 1
            else:
                total = 2

            # see how many copies of that card are still in the deck (or in other hands)
            for c in data.discardPile:
                if ((c.color == color) and (c.value == next_val)):
                    total -= 1
                
            # if no copies of that card are left, all cards of that color can be discarded
            if total == 0:
                return idx

        # Check for cards that we know the value
        if (value != 0):
            # Check if in all the table colors the number are already higher
            if ((len(data.tableCards["red"]) > value) and
                (len(data.tableCards["yellow"]) > value) and
                (len(data.tableCards["green"]) > value) and
                (len(data.tableCards["blue"]) > value) and
                    (len(data.tableCards["white"]) > value)):
                return idx

    return -1


def otherPlayerPlayableCard(playerName, data, hints, version=0):
    """
    Check if another player has a playable card and find the best one, and the type of hint needed
    return the name of that player, and the hint type, and the hint value
    return None, None, None if no cards are playable
    """

    if DBG:
        print("DBG - CHECK RULE 3")


    # Cannot give hints if all Note tokes were used
    if data.usedNoteTokens == 8:
        return None, None, None

    best_card_idx = -1
    # How many copies are left in the deck (or other player hands)
    best_card_criticality = -1
    # If a hint would give complete knowledge to the player, hints already present on that card
    best_card_hint_completeness = -1
    best_card_player = None
    best_card_hint_t = None
    best_card_hint_v = None

    # ordered players from the next of the current player to the previous one (he is not in the list)
    #ordered_players = []
    #skip = True
    #for p in data.players: 
        #if p.name == playerName:
            #skip = False
            #continue
        #if skip == True:
            #continue
        #ordered_players.append(p)
    #skip = False
    #for p in data.players:
        #if p.name == playerName:
            #skip = True
            #continue
        #if skip:
            #continue
        #ordered_players.append(p)

    #for p in ordered_players:
    for p in data.players:
        # Skip the current players' hand: we have no informations 
        if p.name == playerName:
            continue

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

                if DBG:
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
                if ((hint_col == True and hint_val == False) or (hint_col == False and hint_val == True)):
                    completeness = 1

                # if both hints are already given, look for other cards
                if (hint_col and hint_val):
                    pass
                else:
                    # first one, or this is more critical, or this hint gives a complete information and the saved one no
                    if DBG:
                        print("DBG: inside comparison")
                    if((best_card_idx == -1) or
                        (criticality < best_card_criticality) or
                        (completeness > best_card_hint_completeness)
                       ):
                        best_card_player = p.name
                        best_card_idx = idx
                        best_card_criticality = criticality
                        best_card_hint_completeness = completeness

                        if version == 0:
                        # giving hint on color is better, if the hint is not already present
                            if hint_col:
                                best_card_hint_t = "value"
                                best_card_hint_v = value
                            else:
                                best_card_hint_t = "color"
                                best_card_hint_v = color
                            
                        else:
                        # giving hint on value is better, if the hint is not already present
                            if hint_val:
                                best_card_hint_t = "color"
                                best_card_hint_v = color
                            else:
                                best_card_hint_t = "value"
                                best_card_hint_v = value

    return best_card_player, best_card_hint_t, best_card_hint_v


def otherPlayerCriticalCardFirstPosition(playerName, data, hints):
    """
    Check if another player has a critical card in the first position,
    which is the more risky position, since players discard it if no other actions are possible
    return the name of that player, and the hint type, and the hint value
    return None, None, None if no such cards are found
    """

    if DBG:
        print("DBG - CHECK RULE 4")

    # Cannot give hints if all Note tokes were used
    if data.usedNoteTokens == 8:
        return None, None, None

    best_card_idx = -1
    # If a hint would give complete knowledge to the player, hints already present on that card
    best_card_hint_completeness = -1
    best_card_player = None
    best_card_hint_t = None
    best_card_hint_v = None

    # ordered players from the next of the current player to the previous one (he is not in the list)
    #ordered_players = []
    #skip = True
    #for p in data.players: 
        #if p.name == playerName:
            #skip = False
            #continue
        #if skip == True:
            #continue
        #ordered_players.append(p)
    #skip = False
    #for p in data.players:
        #if p.name == playerName:
            #skip = True
            #continue
        #if skip:
            #continue
        #ordered_players.append(p)

    #for p in ordered_players:
    for p in data.players:
        # Skip the current players' hand: we have no informations 
        if p.name == playerName:
            continue
        # we can see hands of other players, with complete info
        hand = p.hand

        # check first card
        card = hand[0]
        color = card.color
        value = card.value

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
        # if it's the last copy: criticality = 1

        # see if it's the first hint, the second or two hints are already given
        hand_h = hints[p.name]
        hint_col = (hand_h[0]["color"] == color)
        hint_val = (hand_h[0]["value"] == value)
        completeness = 0
        if ((hint_col == True and hint_val == False) or (hint_col == False and hint_val == True)):
            completeness = 1

        # if both hints are already given, look for other cards
            if (hint_col and hint_val):
                pass
            else:
                # if this is critical and is the first one, or this hint gives first information and the saved one the second
                if DBG:
                    print("DBG: inside comparison")
                if (criticality == 1 and (
                    (best_card_idx == -1) or
                    (completeness < best_card_hint_completeness)
                )):
                    best_card_player = p.name
                    best_card_hint_completeness = completeness
                    # giving hint on color is better, if the hint is not already present
                    if hint_col:
                        best_card_hint_t = "value"
                        best_card_hint_v = value
                    else:
                        best_card_hint_t = "color"
                        best_card_hint_v = color

    return best_card_player, best_card_hint_t, best_card_hint_v


def otherPlayerDiscardableCard(playerName, data, hints, onlyComplete=True):
    """
    Check if another player has a discardable card, give a hint about it
    two versions: if onlyComplete=True consider only hints that give complete information about the discardable card
    in this way the player will discard that card surely, and won't consider it as a hint for good card
    """

    if DBG:
        print("DBG - CHECK RULE 5")

    # Cannot give hints if all Note tokes were used
    if data.usedNoteTokens == 8:
        return None, None, None

    # ordered players from the next of the current player to the previous one (he is not in the list)
    #ordered_players = []
    #skip = True
    #for p in data.players: 
        #if p.name == playerName:
            #skip = False
            #continue
        #if skip == True:
            #continue
        #ordered_players.append(p)
    #skip = False
    #for p in data.players:
        #if p.name == playerName:
            #skip = True
            #continue
        #if skip:
            #continue
        #ordered_players.append(p)

    #for p in ordered_players:
    for p in data.players:
        # Skip the current players' hand: we have no informations 
        if p.name == playerName:
            continue
        # we can see hands of other players, with complete info
        hand = p.hand
        for idx, card in enumerate(hand):
            color = card.color
            value = card.value
            # Check if that card is discardable
            # If the table has higher or equal value for that color
            if (len(data.tableCards[color]) > 0) and data.tableCards[color][-1].value >= value:
                # see if it's the first hint, the second or two hints are already given
                hand_h = hints[p.name]
                hint_col = (hand_h[idx]["color"] == color)
                hint_val = (hand_h[idx]["value"] == value)
                # if the player already has complete information
                if hint_col and hint_val:
                    continue
                # if the player already has a hint about the color, but not about the value
                elif hint_col:
                    return p.name, "value", value

                # if the player already has a hint about the value, but not about the color
                elif hint_val:
                    return p.name, "color", color

                # if the player has no hints
                # if version is "onlyComplete" do not consider this card
                else:
                    if not onlyComplete:
                        return p.name, "value", value

            # TODO: check if i have duplicate cards
            # TODO: check if in the discard pile there are all the cards for that color that block it
            # TODO: check if in the discard pile there are all the cards for that value that block it

    return None, None, None


def hintWithMoreInfo(playerName, data, hints, version=1):
    """
    Give the hint that gives more informations
    version is the version of this algorithm: different ways of intending "more information"
    """

    if DBG:
        print("DBG - CHECK RULE 6")

    # Go through all the possible hints and save the best,
    # A hint that gives complete information is more valuable than a hint that gives non complete information

    best_player = None
    best_hint_t = None
    best_hint_v = None

    best_n_complete = 0
    best_n_non_complete = 0

    # Look all the other players hands
    for p in data.players:
        # Skip the current players' hand: we have no informations 
        if p.name == playerName:
            continue
        hand = p.hand

        values = [1, 2, 3, 4, 5]
        colors = ["red", "yellow", "green", "blue", "white"]

        # Check all possible hints and count how much new info they would bring
        # Go through all possible hints of type value
        for val in values:
            hint_t = "value"
            hint_v = val
            n_complete = 0
            n_non_complete = 0

            # Go through each card in player's hand
            for idx, card in enumerate(hand):

                # If the card has the same value and the same hint is not already there
                if card.value == val and hints[playerName][idx]["value"] != card.value:
                    n_non_complete += 1

                    # If a hint for the same card but for the other type is present, then this would be a complete hint
                    if hints[playerName][idx]["color"] == card.color:
                        n_non_complete -= 1  # remove the previous +1
                        n_complete += 1

            if n_complete > best_n_complete or n_non_complete > best_n_non_complete:
                # This is now the best hint!
                best_player = p.name
                best_hint_t = hint_t
                best_hint_v = hint_v
                best_n_complete = n_complete
                best_n_non_complete = n_non_complete

        # Go through all possible hints of type color
        for col in colors:
            hint_t = "color"
            hint_v = col
            n_complete = 0
            n_non_complete = 0

            # Go through each card in player's hand
            for idx, card in enumerate(hand):

                # If the card has the same color and the same hint is not already there
                if card.color == col and hints[playerName][idx]["color"] != card.color:
                    n_non_complete += 1

                    # If a hint for the same card but for the other type is present, then this would be a complete hint
                    if hints[playerName][idx]["value"] == card.value:
                        n_non_complete -= 1  # remove the previous +1
                        n_complete += 1

            if version == 0:
                # complete information is always more valuable than non complete
                condition = n_complete > best_n_complete or n_non_complete > best_n_non_complete

            elif version == 1:
                # complete information has the same value as non complete
                condition = 1 * n_complete + n_non_complete > 1 * \
                    best_n_complete + best_n_non_complete

            elif version == 2:
                # complete information has twice the value as non complete
                condition = 2 * n_complete + n_non_complete > 2 * \
                    best_n_complete + best_n_non_complete

            else:
                # complete information has n=version time the value as non complete
                condition = version * n_complete + n_non_complete > version * \
                    best_n_complete + best_n_non_complete

            if condition:
                # This is now the best hint!
                best_player = p.name
                best_hint_t = hint_t
                best_hint_v = hint_v
                best_n_complete = n_complete
                best_n_non_complete = n_non_complete

    return best_player, best_hint_t, best_hint_v


def discardOldestWithNoHints(playerName, data, hints):
    """
    Discard oldest card with no hints
    return the idx of that card, -1 if cannot discard any card, because 0 note tokens were used
    """

    if DBG:
        print("DBG - CHECK RULE 7")

    # Cannot discard any cards because no Note tokens were used
    if data.usedNoteTokens == 0:
        return -1

    hand = hints[playerName]

    best_idx = -1

    # Go through all the cards in the hand
    for idx, card in enumerate(hand):
        value = card["value"]
        color = card["color"]
        # If it has no hints, the first becomes the best
        if value == 0 and color == "":
            best_idx = idx

    # If found one
    if best_idx != -1:
        return best_idx

    # All cards have hints, if i had full knowledge about a surely discardable card
    # I would have already discarded it from a previous rule
    # So discard the first one
    return 0

def riskyPlayableCard(playerName, data, hints, version):
    """
    if no risk in loosing the game and have a possible good card from what I know with the hints,
    play that card
    """

    if DBG:
        print("DBG - CHECK RULE 9")

    
    # If the number of storm tokens used is high 
    # the risk of loosing the game and getting 0 pts is too high
    if data.usedStormTokens >= version:
        return -1
    
    # Check if I have a card with only 1 hint that could be played
    # Note: if it has two info this is surely not playable (rule 1 is passed)
    hand = hints[playerName]
    for idx, card in enumerate(hand):
        color = card["color"]
        value = card["value"]

        # if I know the value but not the color
        if color == "" and value != 0:

            # assume the color to be one of the possible colors
            colors = ["red", "yellow", "green", "blue", "white"]

            for color in colors:

                # If that card would be playable:
                # If it is a 1 and the pile is empty for that color
                # Or If last added in the tableCard for that color has value - 1
                if ((value == 1 and len(data.tableCards[color]) == 0) or
                        (len(data.tableCards[color]) > 0) and data.tableCards[color][-1].value == value - 1):

                    # It's possible that the card has that color only if one or more copies are left in the deck or my hand
                    total = -1
                    if value == 1:
                        total = 3
                    elif value == 5:
                        total = 1
                    else:
                        total = 2

                    # subtract copies of that card in the discardPile
                    for c in data.discardPile:
                        if ((c.color == color) and (c.value == value)):
                            total -= 1
                
                    # subtract copies of that card in the other players' hands
                    for p in data.players:
                        # skip myself
                        if p.name == playerName:
                            continue
                        h= p.hand
                        for c in h:
                            if c.color == color and c.value == value:
                                total -= 1
                
                    # if at least one copy is left
                    if total >= 1:

                        all_ok = True
                        # if the assumption of the color is wrong verify if one or more copies of other colors 
                        # with that value are left, to avoid risking discarding last copy of a card

                        for clr in colors:
                            if clr == color:
                                continue

                            total = -1
                            if value == 1:
                                total = 3
                            elif value == 5:
                                total = 1
                            else:
                                total = 2

                            # subtract copies of that card in the discardPile
                            for c in data.discardPile:
                                if ((c.color == clr) and (c.value == value)):
                                    total -= 1
                            
                            if total <= 1:
                                all_ok = False

                        # Time to risk a play !!
                        if all_ok:
                            return idx

        # if I know the color but not the value
        #if color != "" and value  == 0:

            # Check if that card is playable
            # If it is a 1 and the pile is empty for that color
            # Or If last added in the tableCard for that color has value - 1
            #if ((value == 1 and len(data.tableCards[color]) == 0) or
                    #(len(data.tableCards[color]) > 0) and data.tableCards[color][-1].value == value - 1):
                #valid_cards.append(idx)

    return -1


        # If the card is not what I think, check if other copies of those possible cards are left in game or hands