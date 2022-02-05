# Computational Intelligence 2021-2022

Exam of computational intelligence 2021 - 2022. It requires teaching the client to play the game of Hanabi (rules can be found [here](https://www.spillehulen.dk/media/102616/hanabi-card-game-rules.pdf)).

Author : Giuseppe Salvi, s287583

## Approach
Rule based agent, conservative approach to limit lost matches with 0 points: play a card only if if you are sure that is playable or no other moves are possible.

The agent was designed to play with other agents with different approaches, or even manual players. 
So assumptions on strategies of the other players were not considered.

## Rules
+ Rule 1: the player has a playable card -> action: play it
+ Rule 2: the player has a discardable card -> action: discard it
+ Rule 3: other player has a playable card -> action: give hint
+ Rule 4: other player has critical card in first position -> action: give hint
+ Rule 5: other player has a discardable card -> action: give hint
+ Rule 6: no playable cards but note tokens available -> action: give hint that gives more info
+ Rule 7: all note tokens were used -> action: discard oldest card with no hints
+ Rule 8: default: very risky play -> play oldest card
+ Rule 9: no risk loosing the game and possible good playable card -> action: risky play

## Results
I played the game with multiple instances of the agent with different rule sets and different versions of the rules.
I obtained the best results with the the following rule_set: 
### Rule set
[rule_1, rule_2, rule_3 (version 1), rule_4, rule_5 (complete = True), rule_6 (version 1), rule_9 (version 2, p=0.6), rule_7, rule_8].
Average scores (100+ matches):
+ 2 players: 16.25
+ 3 players: 17.74
+ 4 players: 16.89
+ 5 players: 15.55

## Inspirations
+ https://www.semanticscholar.org/paper/Solving-Hanabi%3A-Estimating-Hands-by-Opponent%27s-in-Osawa/d7a7b4158ceaa20756e9b2f577654d2da1789bc4
+ https://bradbambara.wordpress.com/2017/05/11/a-winning-hanabi-strategy/
+ https://boardgamegeek.com/thread/804762/elusive-25-point-game-tips-effective-hanabi-play

## Server

The server accepts passing objects provided in GameData.py back and forth to the clients.
Each object has a ```serialize()``` and a ```deserialize(data: str)``` method that must be used to pass the data between server and client.

Watch out! I'd suggest to keep everything in the same folder, since serialization looks dependent on the import path (thanks Paolo Rabino for letting me know).

Server closes when no client is connected.

To start the server:

```bash
python server.py <minNumPlayers>
```

Arguments:

+ minNumPlayers, __optional__: game does not start until a minimum number of player has been reached. Default = 2


Commands for server:

+ exit: exit from the server

## Client

To start the server:

```bash
python client.py <IP> <port> <PlayerName>
```

Arguments:

+ IP: IP address of the server (for localhost: 127.0.0.1)
+ port: server TCP port (default: 1024)
+ PlayerName: the name of the player

Commands for client:

+ exit: exit from the game
+ ready: set your status to ready (lobby only)
+ show: show cards
+ hint \<type> \<destinatary>:
  + type: 'color' or 'value'
  + destinatary: name of the person you want to ask the hint to
+ discard \<num>: discard the card *num* (\[0-4]) from your hand
