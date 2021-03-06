d4 = ("d4", "72fdca01-ff61-4dd2-a6b8-43f567f90ff7")
d6 = ("d6", "1f1a643b-2aea-48b2-91c8-96f0dffaad48")
d8 = ("d8", "4165d32c-7b07-4040-8e57-860a95a0dc69")
d10 = ("d10", "3b7cbb3a-4f52-4445-a4a5-65d5dfd9fa23")
d12 = ("d12", "53d1f6b4-03f6-4b8b-8065-d0759309e00d")
d20 = ("d20", "8d139365-b97c-441c-ac1a-34d280352b7a")
plus = ("+", "1b08a785-f745-4c93-b0f1-cdd64c89d95d")
minus = ("-", "b442c012-023f-42d1-9d28-e85168a4401a")
timer = ("Timer", "d59b44ba-cddf-49f9-88f5-1176a305f3d3")
mythicCharge = ("MythicCharge" , "4848acb5-6664-422d-bb65-86a0130212bd")

BoardWidth = 850
BoardHeight = 300
StoryY = -BoardHeight/2
LocationY = StoryY + 190

plunderTypes = [ 'Weapon', 'Spell', 'Armor' , 'Item', 'Ally' ]

showDebug = False #Can be changed to turn on debug

#This function replaces update() which does not wait for async fns like shuffle to complete
def sync():
	i = rnd(0,1)
	
#------------------------------------------------------------
# Utility functions
#------------------------------------------------------------

def debug(str):
	if showDebug:
		whisper(str)
		
def toggleDebug(group, x=0, y=0):
	global showDebug
	showDebug = not showDebug
	if showDebug:
		notify("{} turns on debug".format(me))
	else:
		notify("{} turns off debug".format(me))

def cardFunctionName(card): # Removes special characters from the card name giving a string we can use as a function name
	if card.Name[0].isdigit():
		cardName = "S{}".format(card.Name)
	else:
		cardName = card.Name
	return cardName.replace(' ','').replace('!','').replace("'","").replace('?','').replace('-','')
	
def shuffle(pile, synchronise=False):
	mute()
	if pile is None or len(pile) == 0: return
	pile.shuffle()
	if synchronise:
		sync()
	notify("{} shuffles '{}'".format(me, pile.name))
	
#Return the default x coordinate of the players hero
#We Leave space for 5 piles (Adventure Path, Adventure, Scenario, Ship, Blessings) then place the characters
def PlayerX(player):
	room = int(BoardWidth / (len(getPlayers()) + 5))
	return  room*(player+5) - room/2 - 32 - BoardWidth/2

def LocationX(i, nl):
	room = int(BoardWidth / nl)
	return room*i - room/2 - 32 - BoardWidth/2
	
def numLocations(): #2 more locations than players but modified by the extra locations counter in the shared tab
	n = len(getPlayers())+2+shared.ExtraLocations
	if n < 1:
		return 1
	if n > 8:
		return 8
	return n
	
def num(s):
   if not s: return 0
   try:
      return int(s)
   except ValueError:
      return 0

def eliminated(p, setVal=None):
	val = list(getGlobalVariable("Eliminated"))	
	if setVal is None:
		return val[p._id] == '1'
	if setVal == True:
		val[p._id] = '1'
	else:
		val[p._id] = '0'
	setGlobalVariable("Eliminated", "".join(val))
	return setVal
	
#Check to see if a card at x1,y1 overlaps a card at x2,y2
#Both have size w, h	
def overlaps(x1, y1, x2, y2, w, h):
	#Four checks, one for each corner
	if x1 >= x2 and x1 <= x2 + w and y1 >= y2 and y1 <= y2 + h: return True
	if x1 + w >= x2 and x1 <= x2 and y1 >= y2 and y1 <= y2 + h: return True
	if x1 >= x2 and x1 <= x2 + w and y1 + h >= y2 and y1 <= y2: return True
	if x1 + w >= x2 and x1 <= x2 and y1 + h >= y2 and y1 <= y2: return True
	return False
	
def cardHere(x, y, checkOverlap=True, cards=table):
	cw = 0
	ch = 0
	for c in cards:
		cx, cy = c.position
		if checkOverlap:
			cw = c.width()
			ch = c.height()
		if overlaps(x, y, cx, cy, cw, ch):
			return c
	return None

def cardX(card):
	x, y = card.position
	return x
	
def cardY(card):
	x, y = card.position
	return y

def clearTargets(group=table, x=0, y=0):
	for c in group:
		if c.controller == me or (c.targetedBy is not None and c.targetedBy == me):
			c.target(False)

def findCard(group, model):
	for c in group:
		if c.model == model:
			return c
	return None

#Work out which of the shared piles a card comes from based on its type/subtype
def comesFrom(card):
	if card is None:
		return None
	if card.Type is not None:
		if card.Type in shared.piles:
			return shared.piles[card.Type]
	if card.Subtype is not None and card.Subtype in shared.piles:
		return shared.piles[card.Subtype]
	return None
	
def returnToBox(card):
	locked = False
	if card.Type == '?': # Not visible
		locked = lockPile(shared.piles['Internal'])
		if not locked: return
		group = card.group
		if group == table:
			x, y = card.position
		card.moveTo(shared.piles['Internal']) # Ensures the card properties are visible
	
	dest = comesFrom(card)		
	if dest is None: # Don't know where to put it
		notify("{} Fails to find place for '{}' in the box".format(me, card))
		if locked: # We moved it, so return it to where it started
			if group == table:
				card.moveToTable(x, y)
			else:
				card.moveTo(group)
	else: # Move to the correct pile - aiming to keep in alphabetical order
		card.link(None)
		index = 0
		for c in dest:
			if c.Name >= card.Name:
				break
			index += 1
		if dest.controller != me:
			card.setController(dest.controller) #Pass control to the pile controller and ask them to move it
			remoteCall(dest.controller, "moveCard", [card, dest, index])
		else:
			card.moveTo(dest, index)
	
	if locked:
		unlockPile(shared.piles['Internal'])

# Called remotely to move a card to a pile we control
def moveCard(card, pile, index):
	mute()
	card.moveTo(pile, index)
	
def isOpen(card):
	if card is None or card.Type != 'Location' or card.Name in ['Middle of Nowhere']:
		return False
	return (card.orientation == Rot0 and card.alternate != "B")
	
def isNotPermanentlyClosed(card):
	if card is None or card.Type != 'Location':
		return False
	if card.Name in ('Abyssal Rift','Camel Race','Five-Pointed Sun'): # This location can never be permanently closed
		return True
	if card.Name in ('Middle of Nowhere'): #This location is always permanently closed
		return False
	return card.alternate != "B"
	
#Any card loaded into the player area must be removed from the box otherwise we end up with duplicates
#Get the card controller to find and then delete the card
def inUse(pile):
	mute()
	for card in pile:
		if card.Subtype in shared.piles:
			if shared.piles[card.Subtype].controller != me:
				remoteCall(shared.piles[card.Subtype].controller, "findAndDelete", [me, card])
			else:
				findAndDelete(me, card)

#Find an exact match based on the card model, if none look for a name match
def findAndDelete(who, card):
	mute()
	found = findCard(shared.piles[card.Subtype], card.model)
	if found is None:
		found = findCardByName(shared.piles[card.Subtype], card.Name)
	if found is not None:
		found.delete()
	else:
		notify("{} is using '{}' which is not in the box".format(who, card))

def rollDice(card): #Roll the dice based on the number of tokens
	mute()
	rolled = 0
	dice = ""
	detail = ""
	for die in [ d20, d12, d10, d8, d6, d4 ]:
		count = card.markers[die]
		if count > 0:
			dice += " + {}{}".format(count, die[0])
			detail += " + ["
			while count > 0:
				roll = 1 + int(random() * num(die[0][1:]))
				detail ="{}{}{}".format(detail,roll,"+" if count > 1 else "]")
				rolled += roll
				count -= 1
			card.markers[die] = 0
	
	if card.markers[plus] > 0:
		rolled += card.markers[plus]
		dice = "{} + {}".format(dice, card.markers[plus])
		detail = "{} + {}".format(detail, card.markers[plus])
		card.markers[plus] = 0
	if card.markers[minus] > 0:
		rolled -= card.markers[minus]
		dice = "{} - {}".format(dice, card.markers[minus])
		detail = "{} - {}".format(detail, card.markers[minus])
		card.markers[minus] = 0
	
	if len(dice) > 0:
		playSound("dice")
		notify("{} rolls {} on {}".format(me, dice[3:], card))
		notify("{} = {}".format(detail[3:], rolled))
		return True
	
	return False

def findCardByName(group, name):
	debug("Looking for '{}' in '{}'".format(name, group.name))
	for card in group:
		if card.Name == name:
			return card
	return None
	
def mythicChargeAdd(card, x=0, y=0):
	addToken(card, mythicCharge)
	
def mythicChargeSub(card, x=0, y=0):
	subToken(card, mythicCharge)
	
def d20Add(card, x=0, y=0):
	addToken(card, d20)
	
def d20Sub(card, x=0, y=0):
	subToken(card, d20)
	
def d12Add(card, x=0, y=0):
	addToken(card, d12)

def d12Sub(card, x=0, y=0):
	subToken(card, d12)
	
def d10Add(card, x=0, y=0):
	addToken(card, d10)

def d10Sub(card, x=0, y=0):
	subToken(card, d10)	
	
def d8Add(card, x=0, y=0):
	addToken(card, d8)

def d8Sub(card, x=0, y=0):
	subToken(card, d8)	
	
def d6Add(card, x=0, y=0):
	addToken(card, d6)

def d6Sub(card, x=0, y=0):
	subToken(card, d6)	
	
def d4Add(card, x=0, y=0):
	addToken(card, d4)

def d4Sub(card, x=0, y=0):
	subToken(card, d4)	
		
def plusThree(card, x=0, y=0):
	tokens(card, 3)

def plusTwo(card, x=0, y=0):
	tokens(card, 2)
	
def plusOne(card, x=0, y=0):
	tokens(card, 1)	
	
def minusThree(card, x=0, y=0):
	tokens(card, -3)

def minusTwo(card, x=0, y=0):
	tokens(card, -2)

def minusOne(card, x=0, y=0):
	tokens(card, -1)

# Find the top pile under this card
def overPile(card, onlyLocations=False):
	debug("Checking to see if '{}' is over a pile".format(card))	
	piles = sorted([ c for c in table if c.pile() is not None and (c.Type == 'Location' or not onlyLocations) ], key=lambda c: -c.getIndex)
	x, y = card.position
	return cardHere(x, y, True, piles)
	
def closeLocation(card, perm):
	mute()
	if card.Type != 'Location':
		notify("This is not a location ...")
		return False

	if perm == False:
		card.orientation = Rot90
		notify("{} temporarily closes '{}'".format(me, card))
		return True
	elif card.Name in ('Abyssal Rift','Gate of the Worldwound','Camel Race','Five-Pointed Sun'): # This location cannot be permanently closed
		notify("This location cannot be permanently closed!")
		return False
		
	# Move cards from location pile back to box
	# If we find the Villain then the location is not closed and the Villain is displayed
	# We need to use a pile with full visibility to access the card type
	pile = card.pile()
	visible = shared.piles['Internal']
	if not lockPile(visible): return
	
	debug("Cleaning up pile '{}'".format(pile.name))
	for c in pile:
		c.moveTo(visible)
	
	villain = [ c for c in visible if c.Subtype == 'Villain' ]
	for c in villain:
		notify("You find {} while attempting to close this location".format(c))
		c.moveTo(pile)
				
	if len(pile) > 1:
		shuffle(pile)
	
	if len(villain) > 0: # Close fails - we temporarily close it instead
		card.orientation = Rot90 
		return False
	
	justBuilt = None	
	
	if findScenario(table).Name == 'The Siege of Drezen': #This scenario makes you build the locations one at a time.
		players = len(getPlayers())
		locNum = 1
		if card.Name == 'Paradise Hill' and players > 1:
			nextLoc = 'Celestial Beacon'
			locNum = 2
		elif card.Name == 'Celestial Beacon' and players > 2:
			nextLoc = 'Armory'
			locNum = 3
		elif card.Name == 'Armory' and players > 3:
			nextLoc = 'Watchtower'
			locNum = 4
		elif card.Name == 'Watchtower' and players > 4:
			nextLoc = 'Guardpost'
			locNum = 5
		elif card.Name == 'Guardpost' and players > 5:
			nextLoc = 'Cemetery'
			locNum = 6
		else:
			nextLoc = 'Citadel'
			locNum = 7
	
		if nextLoc == 'Citadel':
			citadel = findCardByName(shared.piles['Location'],'Citadel')
			if citadel is not None:
				citadel.moveToTable(cardX(card)+10,cardY(card))
				citadel.link(shared.piles['Location7'])
				soltengrebbe = findCardByName(shared.piles['Villain'],'Soltengrebbe')
				if soltengrebbe is not None:
					soltengrebbe.moveTo(shared.piles['Location7'])
				m = 0
				while m < players:
					brimorak = findCardByName(shared.piles['Henchman'],'Brimorak')
					if brimorak is not None:
						brimorak.moveTo(shared.piles['Location7'])
					m = m + 1
				shuffle(shared.piles['Location7'])
				justBuilt = None
		elif nextLoc is not None:
			nextLocCard = findCardByName(shared.piles['Location'],nextLoc)
			nextLocCard.moveToTable(cardX(card)+10,cardY(card))
			pileName = 'Location{}'.format(locNum)
			nextLocCard.link(shared.piles[pileName])
			buildLocation(findScenario(table),nextLocCard,shared.piles[pileName])
			cadre = findCardByName(shared.piles['Henchman'],'Worldwound Cadre')
			if cadre is not None:
				cadre.moveTo(shared.piles[pileName])
				shuffle(shared.piles[pileName])
			justBuilt = shared.piles[pileName]
			
	
	for c in visible: #Banish the remaining cards (unless we are at the Garrison)
		debug("Unexplored ... '{}'".format(c))
		if len(villain) == 0 and card.Name == 'Garrison' and c.Subtype in ['Weapon','Armor']:
			c.moveTo(pile)
		elif findScenario(table).Name == 'The Siege of Drezen' and justBuilt is not None: #put all leftover cards into the new location just built
			if justBuilt is not None:
				c.moveTo(justBuilt)
		elif findScenario(table).Name == 'Onslaught on Drezen' and c.Type == 'Bane':
			c.moveTo(pile)
			notify("Move all cards left at the closed location to the Sanctum. Build the Sanctum and add the villain Aponavicius if necessary.")
		else:
			banishCard(c)
			
	if justBuilt is not None:
		shuffle(justBuilt)
	
	unlockPile(visible)	
	
	notify("{} permanently closes '{}'".format(me, card))
	if len(card.Attr4) > 0 and card.Attr4 != "No effect.":
		notify(card.Attr4)
	flipCard(card)
	
	if findScenario(table).Name in ('The Demon\'s Redoubt','The Ivory Sanctum'): #Demon's Redoubt has you build a new location after two locations are closed, and Ivory Sanctum summons two cohorts after first location is closed
		open = [ c for c in table if isNotPermanentlyClosed(c) ]
		openNum = len(open)
		players = len(getPlayers())

		if openNum == players-1 and findScenario(table).Name == 'The Demon\'s Redoubt':
			fourthSphere = findCardByName(table,"Tower of the Fourth Sphere")
			if fourthSphere is not None:
				foo = 0
			else:
				fourthSphere = findCardByName(shared.piles['Location'],"Tower of the Fourth Sphere")
				locNum = len(getPlayers()) + 2
				pileName = 'Location{}'.format(locNum)
				fourthSphere.moveToTable(cardX(card)+50,cardY(card))
				buildLocation(findScenario(table),fourthSphere,shared.piles[pileName])
				notify("Building Tower of the Fourth Sphere location!")
		elif openNum == players+1 and findScenario(table).Name == 'The Ivory Sanctum':
			grillixbee = findCardByName(shared.piles['Cohort'],"Grillixbee")
			jerribeth = findCardByName(shared.piles['Cohort'],"Jerribeth")
			if grillixbee is not None and jerribeth is not None:
				grillixbee.moveToTable(PlayerX(-1)+15,StoryY)
				jerribeth.moveToTable(PlayerX(-1)+25,StoryY)
			else:
				notify("Could not find Grillixbee and Jerribeth. Please retrieve them manually.")
	
	if findScenario(table).Name in ('Twisty Passages'):
		locs = [ c for c in table if c.Type == "Location" and isNotPermanentlyClosed(c)]
		positions = []
		pileNames = []
		i = 0
		for location in locs:
			x = cardX(location)
			y = cardY(location)
			positions.append([x,y])
			locName = getPileName(location)
			pileNames.append(locName)
			location.moveTo(shared.piles['Internal'])
			i = i + 1
		shuffle(shared.piles['Internal'])
		i = 0
		for card in shared.piles['Internal']:
			card.moveToTable(positions[i][0],positions[i][1])
			card.link(shared.piles[pileNames[i]])
			i = i+1
		notify("The locations have been shuffled, leaving their piles in the same spots!")
	return True
	
def cleanupGame(cleanupStory=False):
	for p in getPlayers():
		if p == me:
			cleanupPiles(cleanupStory)
		else:
			remoteCall(p, "cleanupPiles", [cleanupStory])

def cleanupPiles(cleanupStory=False): #Clean up the cards that we control
	for card in table:
		if card.controller == me:
			if card.Type == 'Character':
				if card.Subtype == 'Token':
					card.moveTo(card.owner.hand)
				else:
					card.switchTo() # Display side A of the card as it shows the deck makeup
			elif not cleanupStory and card.Type == 'Boon': # Return displayed cards to the controller's hand
				card.moveTo(me.hand)
			elif cleanupStory or card.Type != 'Story':
				returnToBox(card)
				
	for i in range(8): # Loop through 8 location decks
		pile = shared.piles["Location{}".format(i+1)]
		if pile.controller == me:
			for card in pile:
				returnToBox(card)

	for p in [ 'Blessing Deck', 'Blessing Discard', 'Special', 'Scenario', 'Plunder', 'Internal' ]:
		pile = shared.piles[p]
		if pile.controller == me:
			for card in pile:
				returnToBox(card)
	
#------------------------------------------------------------
# Global variable manipulations function
#------------------------------------------------------------	

# A Global variable is created for each location pile named after the location
# No functional interface is supplied for this however personal globals needed for reconnect are

def storeHandSize(h):
	me.setGlobalVariable('HandSize', str(h))

def getHandSize(p=me):
	#Press Ganged uses the scenario pile to determine the hand size
	scenario = findScenario(table)
	if scenario is not None and  scenario.Name == 'Press Ganged!' and len(shared.piles['Scenario']) <= num(p.getGlobalVariable('HandSize')):
		return len(shared.piles['Scenario'])
	return num(p.getGlobalVariable('HandSize'))
	
def storeFavoured(f):
	me.setGlobalVariable('Favoured', str(f))
	
def storeCohort(c):
	me.setGlobalVariable('Cohort', c)

def getFavoured():
	return eval(me.getGlobalVariable('Favoured'))

def getCohort():
	return me.getGlobalVariable('Cohort')
	
def storeSiege(m):
	me.setGlobalVariable('Siege',m)
	
def getSiege():
	return eval(me.getGlobalVariable('Siege'))
	
def storeCards(s):
	me.setGlobalVariable('Cards', s)
	
def getCards():
	return me.getGlobalVariable('Cards')

def lockInfo(pile):
	if pile is None: return (None, 0)
	lock = getGlobalVariable(pile.name)
	if len(lock) == 0:
		return (None, 0)
	info = lock.split()
	return (info[0], num(info[1]))
	
def lockPile(pile):
	mute()
	if pile is None: return False
	# Attempt to lock the shared pile
	# Write the player name and count into a global named after the pile
	#who, count = lockInfo(pile)
	#if who != None and who != me.name:
	#	whisper("{} has temporarily locked the game - please try again".format(who))
	#	return False
	#	
	#if pile.controller != me:
	#	pile.setController(me)
	#	sync()
	#setGlobalVariable(pile.name, "{} {}".format(me.name, count+1))
	return True

def unlockPile(pile):
	mute()
	if pile is None: return False
	who, count = lockInfo(pile)
	if who is None:
		debug("{} tries to unlock pile '{}' - not locked".format(me, pile.name))
		return False
	if who != me.name:
		debug("{} tries to unlock pile '{}' - locked by {}".format(me, pile.name, info[0]))
		return False
	if count <= 1:
		setGlobalVariable(pile.name, None)
	else:
		setGlobalVariable(pile.name, "{} {}".format(me.name, count-1))
	return True

#Look at the global variables to determine who was the active player on the given turn
def getPlayer(turn):
	for var in [ 'Current Turn', 'Previous Turn' ]:
		info = getGlobalVariable(var)
		if len(info) > 0:
			t, p = info.split('.')
			if int(t) == turn:
				for player in getPlayers():
					if player.name == p:
						return player
	return None
	
#---------------------------------------------------------------------------
# Call outs
#---------------------------------------------------------------------------

def setGlobals():
	mute()
	setGlobalVariable('Fleet', '[]')
	
def deckLoaded(player, groups):
	mute()

	if player != me:
		return
		
	isShared = False
	for p in groups:
		if p.name in shared.piles:
			isShared = True
		if p.name == 'Internal': # Fleet cards are loaded into the Internal pile
			# Store each ship in the fleet in a global variable so we know where to put them when they go back to the box
			fleet = [ c.Name for c in shared.piles[p.name] ]
			setGlobalVariable('Fleet', str(fleet))
			for c in shared.piles[p.name]:
				c.moveTo(shared.piles['Ship'])
		
	if not isShared: # Player deck loaded
		playerSetup()
	
def startOfTurn(player, turn):
	mute()
	debug("Start of Turn {} for player {}".format(turn, player))
	
	clearTargets()
	if player == me: # Store my details in the global variable
		setGlobalVariable("Previous Turn", getGlobalVariable("Current Turn"))
		setGlobalVariable("Current Turn", "{}.{}".format(turn, player.name))
			
	lastPlayer = getPlayer(turn-1)
	debug("Last Player = {}, player = {}, me = {}".format(lastPlayer, player, me))
	if lastPlayer is not None and me == lastPlayer:
		drawUp(me.hand)
		
	# Pass control of the shared piles and table cards to the new player
	debug("Processing table ...")
	for card in table: 
		if card.controller == me: # We can only update cards we control	
			if card.orientation != Rot0: #Re-open any temporarily closed locations
				card.orientation = Rot0	
			if card.Type == 'Character':
				if card.owner == me: #Highlight my avatar
					if player == me: # I am the active player
						card.sendToFront()
						card.highlight = "#82FA58" # Green
					elif eliminated(me):
						card.highlight = "#FF0000" # Red
					else:
						card.highlight = None
			elif player != me: #Pass control of all non-character cards to the new active player
				card.setController(player)
	
	debug("Processing shared piles ...")	
	for name in shared.piles:
		if shared.piles[name].controller == me and player != me: # Hand over control to the new player
			shared.piles[name].setController(player)
		
	if player == me:
		sync() # wait for control of cards to be passed to us
		# Perform scenario specific actions
		scenario = findScenario(table)
		if scenario is not None:
			fn = cardFunctionName(scenario)
			if fn in globals():
				globals()[fn]('StartOfTurn')
		advanceBlessingDeck()	
	
#
# Scenario specific functions - called once during setup and then at the start of each turn
# The function must be named exactly as the Scenario card with the spaces removed
#
def HereComestheFlood(mode):
	if mode == 'Setup':
		locs = [c for c in table if c.Type == 'Location']
		for loc in locs:
			randBlessing = shared.piles['Blessing'].random()
			randBlessing.moveTo(loc.pile())
			randAlly = shared.piles['Ally'].random()
			randAlly.moveTo(loc.pile())
			shuffle(loc.pile())

	if mode == 'StartOfTurn':
		mute()
		#Pick a random location
		locs = [ c for c in table if c.Type == 'Location' ]
		loc = locs[int(random()*len(locs))]
		#Move 1d4 cards from that location to the table
		moved = 0
		toMove = 1+int(random()*4)
		for c in loc.pile().bottom(toMove):
			c.moveTo(shared.piles['Special'])
			moved += 1
		if toMove == moved:
			notify("{} moves {} cards from {} to Black Magga".format(me, moved, loc))
		else:
			notify("{} moves {} cards (rolled {}) from {} to Black Magga".format(me, moved, toMove, loc))

def SandpointUnderSiege(mode):
	if mode == 'StartOfTurn':
		mute()
		#Pick a random open location
		locs = [ c for c in table if isOpen(c) ]
		loc = locs[int(random()*len(locs))]
		if len(loc.pile()) == 0:
			notify("Random open location '{}' has no cards".format(loc))
		else:
			c = loc.pile().top()
			x, y = loc.position
			c.moveToTable(x, y+14)
			notify("{} reveals '{}' as the top card of '{}'".format(me, c, loc))
			if c.Type == 'Boon':
				banishCard(c)
			elif c.Type == 'Bane':
				notify("{} shuffles '{}' back into '{}'".format(me, c, loc))
				c.moveTo(loc.pile())
				shuffle(loc.pile(), True)
			
def TheTolloftheBell(mode):
	if mode == 'Setup':
		mute()
		#Deal an extra henchman to the first location (Scar Bay) if we have an even number of players
		zombie = findCardByName(shared.piles['Henchman'], 'Scurvy Zombie')
		if zombie is None: return
		zombie.moveTo(shared.piles['Location1'])
		shuffle(shared.piles['Location1'])
	
def TheGrindylowandtheWhale(mode): # setup requires each player to move a random ally into the Scenario pile
	if mode == 'Setup':
		mute()
		for p in getPlayers():
			if p == me:
				donateAlly(me)
			else:
				remoteCall(p, "donateAlly", [ me ])
		sync()
		#Find all the allies on the table (they are face down at 0,0) and move to the Scenario pile
		facedown = [c for c in table if not c.isFaceUp]
		for c in facedown:
			x, y = c.position
			if x == 0 and y == 0:
				c.moveTo(shared.piles['Scenario'])				
		shuffle(shared.piles['Scenario'])

def LandfallonColyphyr(mode):
	if mode == 'Setup':
		mute()
		abyssalRiver = findCardByName(table,"Abyssal River")
		kestoglyr = findCardByName(shared.piles['Henchman'],"Kestoglyr Mantiel")
		if abyssalRiver is not None and kestoglyr is not None:
			kestoglyr.moveTo(abyssalRiver.pile())
			shufflePile(abyssalRiver.pile())
		
def TheFeastofSpoils(mode): #In Feast of Spoils, there are 8 Shipwreck Henchmen in the Blessings deck
	if mode == 'Setup':
		mute()
		i = 0
		while i < 8:
			shipwreck = findCardByName(shared.piles['Henchman'],"Shipwreck")
			if shipwreck == None:
				whisper("Not enough Shipwrecks!")
			else:
				shipwreck.moveTo(shared.piles['Blessing Deck'])
			i=i+1
		i = 0
		while i < 22:
			shared.piles['Blessing'].random().moveTo(shared.piles['Blessing Deck'])
			i=i+1
		
def TheLandoftheBlind(mode): #In The Land of the Blind, there are 6 Gholdakos in the blessings deck, and when one is found, it is added to a random open location
	if mode == 'Setup':
		mute()
		i = 0
		while i < 6:
			gholdako = findCardByName(shared.piles['Henchman'],"Gholdako")
			if gholdako == None:
				whisper("Not enough Gholdakos!")
				return
			gholdako.moveTo(shared.piles['Blessing Deck'])
			i = i+1
	elif mode == 'StartOfTurn':
		i = 0
		for c in table:
			if c.Name == 'Gholdako':
				i = i + 1
		if i > 5:
			gameOver(True)
			
def ASandstormofMalevolentWill(mode): #In A Sandstorm of Malevolent Will, four blessings are replaced with Sandstorm villains.
	if mode == 'Setup':
		mute()
		i = 0
		while i < 4:
			sandstorm = findCardByName(shared.piles['Villain'],"Sandstorm")
			if sandstorm == None:
				whisper("Not enough Sandstorms!")
				return
			sandstorm.moveTo(shared.piles['Blessing Deck'])
			i = i+1
		shuffle(shared.piles['Blessing Deck'])

def ForgedinFlames(mode): #Five blessings are replaced with Conflagration henchmen
	if mode == 'Setup':
		mute()
		i = 0
		while i < 5:
			conflagration = findCardByName(shared.piles['Henchman'],"Conflagration")
			if conflagration == None:
				whisper("Not enough Conflagrations!")
				return
			conflagration.moveTo(shared.piles['Blessing Deck'])
			i = i+1
		shuffle(shared.piles['Blessing Deck'])
			
def NocticulasAttention(mode):
	if mode == 'Setup':
		mute()
		setGlobalVariable('nocticula',0)
		
def TheFallofKenabres(mode): #In The Fall of Kenabres, add Khorramzadeh to the blessings deck, and when he's found, he deals damage to all players and re-shuffles
	if mode == 'Setup':
		mute()
		khorramzadeh = findCardByName(shared.piles['Villain'],"Khorramzadeh")
		if khorramzadeh == None:
			whisper("Could not find Khorramzadeh to add him to the Blessings Deck!")
			return
		khorramzadeh.moveTo(shared.piles['Blessing Deck'])

def MuminofrahsAmusement(mode):
	if mode == 'Setup':
		mute()
		cameltrops1 = findCardByName(shared.piles['Villain'],"Cameltrops")
		if cameltrops1 == None:
			whisper("Could not find sufficient Cameltrops to add to the Blessings Deck!")
			return		
		cameltrops1.moveTo(shared.piles['Blessing Deck'])	
		
		cameltrops2 = findCardByName(shared.piles['Villain'],"Cameltrops")
		if cameltrops2 == None:
			whisper("Could not find sufficient Cameltrops to add to the Blessings Deck!")
			return		
		cameltrops2.moveTo(shared.piles['Blessing Deck'])
		
		cameltrops3 = findCardByName(shared.piles['Villain'],"Cameltrops")
		if cameltrops3 == None:
			whisper("Could not find sufficient Cameltrops to add to the Blessings Deck!")
			return
		cameltrops3.moveTo(shared.piles['Blessing Deck'])
		
		charioteers = findCardByName(shared.piles['Villain'],'Cultist Charioteers')
		if charioteers == None:
			whisper ("Could not find villain Cultist Charioteers!")
			return
		charioteers.moveToTable(PlayerX(-1)+15,StoryY)
		
def InSearchofChisisek(mode):
	if mode == 'Setup':
		mute()
		cultist1 = findCardByName(shared.piles['Henchman'],"Forgotten Pharaoh Cultist")
		if cultist1 == None:
			whisper("Could not find enough Forgotten Pharaoh Cultists!")
			return
		cultist1.moveTo(shared.piles['Blessing Deck'])
		
		cultist2 = findCardByName(shared.piles['Henchman'],"Forgotten Pharaoh Cultist")
		if cultist2 == None:
			whisper("Could not find enough Forgotten Pharaoh Cultists!")
			return
		cultist2.moveTo(shared.piles['Blessing Deck'])
		
		cultist3 = findCardByName(shared.piles['Henchman'],"Forgotten Pharaoh Cultist")
		if cultist3 == None:
			whisper("Could not find enough Forgotten Pharaoh Cultists!")
			return
		cultist3.moveTo(shared.piles['Blessing Deck'])
		
		cultist4 = findCardByName(shared.piles['Henchman'],"Forgotten Pharaoh Cultist")
		if cultist4 == None:
			whisper("Could not find enough Forgotten Pharaoh Cultists!")
			return
		cultist4.moveTo(shared.piles['Blessing Deck'])
		
		cultist5 = findCardByName(shared.piles['Henchman'],"Forgotten Pharaoh Cultist")
		if cultist5 == None:
			whisper("Could not find enough Forgotten Pharaoh Cultists!")
			return
		cultist5.moveTo(shared.piles['Blessing Deck'])
		
		cultist6 = findCardByName(shared.piles['Henchman'],"Forgotten Pharaoh Cultist")		
		if cultist6 == None:
			whisper("Could not find enough Forgotten Pharaoh Cultists!")
			return
		cultist6.moveTo(shared.piles['Blessing Deck'])


def StingOperation(mode):
	if mode == 'Setup':
		mute()
		locs = [card for card in table if card.Type == "Location"]
		for card in locs:
			larvae = findCardByName(shared.piles['Henchman'],"Stolen Larvae")
			larvae.moveTo(card.pile())
			shuffle(card.pile())
		
		
def InsideLucrehold(mode): #In Inside Lucrehold, Brinebones is shuffled into the blessings deck
	if mode == 'Setup':
		mute()
		brinebones = findCardByName(shared.piles['Villain'],"Brinebones")
		if brinebones == None:
			whisper("Cannot find Brinebones!")
		else:
			brinebones.moveTo(shared.piles['Blessing Deck'])
		
def AudiencewiththeInheritor(mode): #In Audience with the Inheritor, Lady of Valor is shuffled into the blessings deck
	if mode == 'Setup':
		mute()
		inheritor = findCardByName(shared.piles['Villain'],"Lady of Valor")
		if inheritor == None:
			whisper("Cannot find Lady of Valor!")
		else:
			inheritor.moveTo(shared.piles['Blessing Deck'])
		
def IslandsoftheDamned(mode):
	if mode == 'Setup':
		mute()
		i = 0
		while i < 4:
			shared.piles["Location1"].random().moveTo(shared.piles["Location2"])
			i = i + 1
		
def TheDemonsRedoubt(mode):
	if mode == 'Setup':
		locs = [card for card in table if card.Type == "Location"]
		for card in locs:
			grimslake = findCardByName(shared.piles['Henchman'],"Grimslake")
			grimslake.moveTo(card.pile())
		
def S02DWhoRulesHellHarbor(mode): #In Who Rules Hell's Harbor, display the Devil's Pallor so that it can't be chosen by a player
	if mode == 'Setup':
		devil = findCardByName(shared.piles['Ship'],'Devil\'s Pallor')
		devil.moveToTable(PlayerX(-1)+15,StoryY)
		whisper("Make sure to load the special ship deck 'Ships for 0-2D', and place them on the board!")
		
def S02ALovesLaboursLost(mode):	#In Love's Labours Lost, display Heartbreak Hinsin next to the scenario card
	if mode == 'Setup':
		hinsin = findCardByName(shared.piles['Ally'],'Heartbreak Hinsin')
		hinsin.moveToTable(PlayerX(-1)+15,StoryY)
		
def ChainsofSilver(mode): #In Chains of Silver, an extra henchman is shuffled into the first location.
	if mode == 'Setup':
		ekram = findCardByName(shared.piles['Henchman'],'Ekram Iffek')
		whisper("searched for Ekram")
		if ekram is not None:
			whisper("Ekram found")
			ekram.moveTo(shared.piles['Location1'])
			shuffle(shared.piles['Location1'])
		else:
			whisper("Could not find henchman Ekram!")
			return

def ThoseWhoDwellinDarkness(mode): #In this scenario, a second set of henchmen is added to the decks.
	if mode == 'Setup':
		numLocs = numLocations()
		i = 0
		while i < 3:
			elegiac = findCardByName(shared.piles['Henchman'],'Elegiac Compass')
			if elegiac is not None:
				elegiac.moveTo(shared.piles['Special'])
			else: 
				whisper("Could not find enough Elegiac Compasses!")
				err = i
				break
			i=i+1
		randBless = numLocs - i
		i = 0
		while i < randBless:

			blessing = shared.piles['Blessing'].random()
			blessing.moveTo(shared.piles['Special'])
			i += 1

		i = 1
		while i <= numLocs:
			random = shared.piles['Special'].random()
			random.moveTo(shared.piles['Location{}'.format(locNum)])
			i += 1

			
#Pick a random ally from the player piles, move it to the table and pass control to the supplied player
def donateAlly(who):
	mute()
	allies = [ c for c in me.hand if c.Subtype == 'Ally' ]
	for name in me.piles:
		allies.extend([ c for c in me.piles[name] if c.Subtype == 'Ally' ])
	if len(allies) > 0:
		ally = allies[int(random()*len(allies))]
		debug("{} donates {} to {}".format(me, ally, who))
		ally.moveToTable(0, 0, True) # Move face down to the centre of the table
		ally.setController(who)

def checkMovement(player, card, fromGroup, toGroup, oldIndex, index, oldX, oldY, x, y, isScriptMove, highlight=None, markers=None):
	checkMovementAll(player, card, fromGroup, toGroup, oldIndex, index, oldX, oldY, x, y, False, highlight, markers)
	
def checkScriptMovement(player, card, fromGroup, toGroup, oldIndex, index, oldX, oldY, x, y, isScriptMove, highlight=None, markers=None):
	checkMovementAll(player, card, fromGroup, toGroup, oldIndex, index, oldX, oldY, x, y, True, highlight, markers)
		
#
#Card Move Event
# Enforce game logic for ships, avatars and blessing deck
#
def checkMovementAll(player, card, fromGroup, toGroup, oldIndex, index, oldX, oldY, x, y, isScriptMove, highlight, markers, faceup=None):
	mute()
	bd = shared.piles['Blessing Discard']
	if fromGroup == bd or toGroup == bd or me.isActivePlayer: #Check to see if the current blessing card needs to change
		bx = PlayerX(0)
		by = StoryY	
		bc = None #Temp blessing card	
		for c in table:
			if c.pile() == shared.piles['Blessing Deck']:
				bx, by = c.position
				if fromGroup == bd or toGroup == bd: # Tidy up the temp blessing card
					if c.controller == me:
						c.link(None)
						c.delete()
				else:
					bc = c
				break
					
		if me.isActivePlayer and len(bd) > 0 and bc is None: # Create a copy of the top card
			bc = table.create(bd.top().model, bx, by)
			bc.link(shared.piles['Blessing Deck'])
	
	if player != me or isScriptMove or card.Type != 'Character' or card.Subtype != 'Token': # Nothing to do
		return	

	# Our Avatar has moved
	if fromGroup == table and toGroup != table: # Did we move the avatar off the table
		# Don't allow this
		card.moveToTable(oldX, oldY)
		return
	if fromGroup != table and toGroup == table: # Did we move the avatar onto the table
		# If the scenario hasn't been set up yet return the avatar to hand and issue a warning
		locs = [ c for c in table if c.Type == 'Location' ]
		if len(locs) == 0:
			whisper("Ensure the scenario is set up before placing {} at your starting location".format(card))
			card.moveTo(fromGroup)
			return
		playerReady(card)
		
def playerReady(card):
	mute()
	#Ensure side B of the character card is face up
	for c in table:
		if c.owner == me and c.Type == 'Character' and c != card:
			c.switchTo('B')

	debug("{} is ready".format(me))
	#Move all player card (Boons) to Discarded pile - then shuffle ready for dealing
	for pile in [ me.hand, me.Buried, me.deck ]:
		for c in pile:
			if c.Type == 'Character':
				c.moveTo(me.hand)
			elif c.Type in ('Feat','Cohort'):
				c.moveTo(me.Buried)
			else:
				c.moveTo(me.Discarded)
	shuffle(me.Discarded, True)
	size = len(me.Discarded)
	choices = getFavoured()					
	if 'Your choice' in choices: # Ignore the stored value and make a list of the card types in the deck
		choices = []
		for card in me.Discarded:	
			if card.Subtype not in choices:
				choices.append(card.Subtype)
			if card.Subtype == 'Loot': # Loots have a secondary type too
				if card.Subtype2 not in choices:
					choices.append(card.Subtype2)
		
	#Prompt user to select favoured card type
	choice = None
	charName = None
	if len(choices) > 1:
		if choices[0] == 'Special': #for handling strange favored cards
			charName = choices[1]
			favoured = None
		else:	
			while choice == None or choice == 0:
				choice = askChoice("Favoured Card Type", choices)
			favoured = choices[choice-1]
	elif len(choices) == 1:
		favoured = choices[0]
	else:
		favoured = None
	handSize = getHandSize()
	ci = 0
	
	if favoured is not None: # If a favoured card type is defined skip cards until we reach one
		for card in me.Discarded:
			if card.Subtype == favoured or (card.Subtype == 'Loot' and card.Subtype2 == favoured): break
			ci += 1
	
	#A few characters have strange favored card requirements. We handle those here.
	if charName is not None:
		if charName == 'Estra':
			for card in me.Discarded:
				if card.Subtype == 'Loot' and card.Name == 'Honaire': break
				ci += 1
		if charName == 'Ahmotep':
			for card in me.Discarded:
				traits = card.Traits.split()
				if 'Staff' in traits: break
				ci += 1
		if charName == 'Ezren':
			notify("In EZREN line 1013")
			for card in me.Discarded:
				traits = card.Traits.split()
				notify("Traits are {}".format(traits[0]))
				if 'Attack' in traits: break
				ci += 1
	
	if ci >= size:
		ci = 0
		notify("{} has an invalid deck - no favoured cards ({})".format(me, favoured))
	
	if ci > 0: #Move the top cards to deck so that the favoured card is at the top of the Discarded pile
		for card in me.Discarded.top(ci):
			card.moveToBottom(me.Discarded)

	for c in me.Discarded.top(handSize):
		c.moveTo(me.hand)
	#Move the rest of the cards into the deck
	for card in me.Discarded:
		card.moveTo(me.deck)
	
	cohort = getCohort()
	if cohort is not None:
		cohortCard = findCardByName(me.hand,cohort)
		if cohortCard is not None:
			whisper("You already have your cohort in your hand!")
		else:
			cohortCard = findCardByName(shared.piles['Cohort'],cohort)
			if cohortCard is None:
				notify("Could not find cohort {} in cohort pile, checking your cards!".format(cohort))
				cohortCard = findCardByName(me.buried,cohort)
				if cohortCard is None:
					cohortCard = findCardByName(me.deck,cohort)
					if cohortCard is None:
						notify("Cohort {} is not in your cards either, did you banish it?".format(cohort))
					else:
						cohortCard.moveTo(me.hand)
				else:
					cohortCard.moveTo(me.hand)
			else:
				cohortCard.moveTo(me.hand)
	
	sync()
	#The first player to drag to the table becomes the active player
	tokens = [ c for c in table if c.Subtype == 'Token' ]
	if len(tokens) == 1:
		#Check to see who the active player is
		active = None
		for p in getPlayers():
			if p.isActivePlayer:
				active = p
				break
		if active is None: # At the start of a game no one is active but anyone can set the active player
			makeActive(me)
		else:
			remoteCall(active, "makeActive", [me])

def makeActive(who):
	mute()
	if who != me:
		debug("{} passes control to {}".format(me, who))
	who.setActivePlayer()

# Called when a player draws an arrow between two cards (or clears an arrow)
# If the source card has dice on it, they are moved to the destination
# This is done in two parts, the controller of the dst card adds dice based on the src
# Then the controller of the src card removes the dice on it
def passDice(player, src, dst, targeted):
	mute()
	if targeted and dst.controller == me:	
		whisper("dst controller is {}".format(dst.controller))
		dice=""
		for m in [ d20, d12, d10, d8, d6, d4 ]:
			if src.markers[m] > 0:
				dice = "{} + {}{}".format(dice, src.markers[m], m[0])
				dst.markers[m] += src.markers[m]
		if src.markers[plus] > 0:
			dice = "{} + {}".format(dice, src.markers[plus])
			dst.markers[plus] += src.markers[plus]
		if src.markers[minus] > 0:
			dice = "{} - {}".format(dice, src.markers[minus])
			dst.markers[minus] += src.markers[minus]
		if src.controller != me:
			remoteCall(src.controller, "clearDice", [src])
		else:
			clearDice(src)
		notify("{} Moves {} from {} to {}".format(player, dice[3:], src, dst))

# Remove all dice from the card
def clearDice(card):
	mute()
	whisper("Clearing dice on {}".format(card))
	for m in [ d20, d12, d10, d8, d6, d4, plus, minus ]:
		if card.markers[m] > 0:
			card.markers[m] = 0	
			
def clearMythCharges(card):
	mute()
	whisper("Clearing mythic charges on {}".format(card))
	if card.markers[mythicCharge] > 0:
		card.markers[mythicCharge] = 0
		
#---------------------------------------------------------------------------
# Table group actions
#---------------------------------------------------------------------------

# Roll on the Skull and Shackles Plunder table
def rollPlunder(unused, x=0, y=0):
	r = int(random()*6)
	if r < len(plunderTypes):
		notify("{} rolls a {} on the plunder table ({})".format(me, r+1, plunderTypes[r]))
	else:
		notify("{} rolls a {} on the plunder table (Your choice)".format(me, r+1))
		
# Remove targeting arrows after a check
def clearTargets(group=table, x=0, y=0):
	for c in group:
		if c.controller == me or (c.targetedBy is not None and c.targetedBy == me):
			c.target(False)
			
#Table action - prompts the player to pick an adventure path, an adventure and a scenario
#If there is already a scenario on the table clear it away
def pickScenario(group=table, x=0, y=0):
	mute()
	
	#If any of the players haven't loaded their deck we abort
	for p in getPlayers():
		if getHandSize(p) == 0:
			whisper("Please wait until {} has loaded their deck and then try again".format(p))
			return
	
	#Take control of the shared piles
	for name in shared.piles:
		if shared.piles[name].controller != me:
			shared.piles[name].setController(me)
	sync()
	
	story = [ card for card in group if card.Type == 'Story' ]
	if len(story) > 0:
		if not confirm("Clear the current game?"):
			return
		cleanupGame(True)
		sync() #wait for other players to tidy up their cards
	
	autobanish = False # Rise of the Runelords and Skull and Shackles adventure paths have special rules for banishing cards with the Basic and Elite traits
	setGlobalVariable('Previous Turn', '')
	setGlobalVariable('Current Turn', '')
	setGlobalVariable('Remove Basic', '')
	setGlobalVariable('Remove Elite', '')
	storeSiege(False)
	
	#Pick the new Scenario
	paths = [ card.Name for card in shared.piles['Story'] if card.Subtype == 'Adventure Path' ]
	if len(paths) > 0:
		paths.append("None")
		choice = askChoice("Choose Adventure Path", paths)
	else:
		choice = 0
	if choice <= 0 or paths[choice-1] == 'None': # Not using an adventure path
		adventures = [ card.Name for card in shared.piles['Story'] if card.Subtype == 'Adventure' ]
		adventures.append("None")
	else:
		path = findCardByName(shared.piles['Story'], paths[choice-1])
		autobanish = path.Name in ['Rise of the Runelords', 'Skull and Shackles','Wrath of the Righteous','Mummy\'s Mask']
		path.moveToTable(PlayerX(-4),StoryY)
		flipCard(path)
		loaded = [ card.Name for card in shared.piles['Story'] if card.Subtype == 'Adventure' ]
		adventures = []
		for o in path.Attr1.splitlines(): # Build up a list of options that have been loaded and in the order given
			if o in loaded:
				adventures.append(o)
				
		if path.Name == "Wrath of the Righteous":
			redemption = findCardByName(shared.piles['Support'],"Redemption")
			if redemption is not None:
				redemption.moveToTable(PlayerX(-5),StoryY)
				q = 5
				for p in redemption.Attr1.splitlines():
					foundRedemption = findCardByName(shared.piles['Support'],p)
					if foundRedemption is not None:
						foundRedemption.moveToTable(PlayerX(-5),StoryY+q)
						q = q + 5
	
	if len(adventures) < 2:
		choice = len(adventures)
	else:
		choice = askChoice("Choose Adventure", adventures)
	if choice <= 0 or adventures[choice-1] == 'None': # Not using an adventure card
		scenarios = [ card.Name for card in shared.piles['Story'] if card.Subtype == 'Scenario' ]
	else:
		adventure = findCardByName(shared.piles['Story'], adventures[choice-1])
		adventure.moveToTable(PlayerX(-3), StoryY)
		if autobanish:
			if num(adventure.Abr) >= 3:
				setGlobalVariable("Remove Basic", "1")
			if num(adventure.Abr) >= 5:
				setGlobalVariable("Remove Elite", "1")
		flipCard(adventure)
		loaded = [ card.Name for card in shared.piles['Story'] if card.Subtype == 'Scenario' ]
		scenarios = []
		for o in adventure.Attr1.splitlines(): # Build up a list of options that have been loaded and in the order given
			if o in loaded:
				scenarios.append(o)
	if len(scenarios) < 2:
		choice = len(scenarios)
	else:
		choice = askChoice("Choose Scenario", scenarios)
	if choice > 0:
		scenario = findCardByName(shared.piles['Story'], scenarios[choice-1])
		scenario.moveToTable(PlayerX(-2),StoryY)
		scenarioSpecific = scenarioSetup(scenario)	
		
		#If we loaded a fleet then pick a ship		
		fleet = eval(getGlobalVariable('Fleet'))
		if len(fleet) > 0 and scenario.Name not in ['0-6B The Battle of Abendego','0-6F Lost in the Storm']:
			anchorage = scenarioSpecific['anchorage']
			if len(fleet) == 1:
				choice = 1
			else:
				choice = askChoice("Choose Your Ship", fleet)
			ship = findCardByName(shared.piles['Ship'], fleet[choice-1])
			fleet.pop(choice-1)
			ship.moveToTable(PlayerX(-1), StoryY)
			ship.link(shared.piles['Plunder'])
			addPlunder(ship)
			if anchorage is not None:
				x, y = anchorage.position
				ship.moveToTable(x+3*anchorage.width()/4, y-anchorage.height()/4)
				ship.setIndex(0) # Move underneath the location and slightly offset
				
		if scenario.Name == "The Armada": #In The Armada, make a new fleet deck after placing your ship
			newShipName = fleet[int(random()*len(fleet))]
			fleetShip = findCardByName(shared.piles['Ship'],newShipName)
			fleet.remove(newShipName)
			if fleetShip == None:
				whisper("Failed to find ships in loaded Fleet pile")
			else:
				fleetShip.moveToTable(PlayerX(-5),StoryY)
				fleetShip.link(shared.piles['Special'])
				i = 0
				while i < 3:
					newShipName = fleet[int(random()*(len(fleet)-i))]
					newShip = findCardByName(shared.piles['Ship'],newShipName)
					fleet.remove(newShipName)
					if newShip == None:
						whisper("Not enough ships in fleet!")
						return
					else:
						newShip.moveTo(shared.piles['Special'])
					i = i + 1
			whisper("Remember to summon ships one-by-one! Do not choose 'Reveal random cards' for ships!")
	
		#Handle a scenario-specific cohort if there is one
		i = 1
		cohortNum = int(scenarioSpecific['cohortNum'])
		if cohortNum > 1:
			whisper("Please choose one scenario-specific cohort per player (at most) and move it to your hand.")
		
		while i <= cohortNum:
			cohort = str(scenarioSpecific['cohort{}'.format(i)])
			cohortCard = findCardByName(shared.piles['Cohort'],cohort)
			if cohortCard is not None:
				cohortCard.moveToTable(PlayerX(-1)+(i*10),StoryY)
			else:
				whisper("Could not find cohort {}".format(cohortCard))
			i = i + 1
			
		#Handle troop placement if there is one
		troop = scenarioSpecific['troopName']
		if troop != '':
			troopCard = findCardByName(shared.piles['Support'],troop)
			if troopCard is not None:
				troopCard.moveToTable(PlayerX(-1),StoryY)
				j = 5
				for n in troopCard.attr1.splitlines():
					medal = findCardByName(shared.piles['Support'],n)
					if medal is not None:
						medal.moveToTable(PlayerX(-1),StoryY+j)
					j = j + 5
			else: 
				notify("Could not find troop card {}!".format(troop))

def nextTurn(group=table, x=0, y=0):
	mute()
	# Only the current active player can do this
	if not me.isActivePlayer:
		whisper("Only the active player may perform this operation")
		return
	players = getPlayers()
	nextID = (me._id % len(players)) + 1
	while nextID <> me._id:
		for p in players:
			if p._id == nextID and not eliminated(p):
				p.setActivePlayer()
				return
		nextID = (nextID % len(players)) + 1
	me.setActivePlayer()
	
def randomHiddenCard(group=table, x=0, y=0):
	pile, trait = cardTypePile()
	if pile is None: return
	if pile.controller != me:
		remoteCall(pile.controller, "randomCardN", [me, pile, trait, x, y, 1, True])
	else:
		randomCardN(me, pile, trait, x, y, 1, True)
	
def randomCard(group=table, x=0, y=0):
	pile, trait = cardTypePile()
	if pile is None: return
	if pile.controller != me:
		remoteCall(pile.controller, "randomCardN", [me, pile, trait, x, y, 1])
	else:
		randomCardN(me, pile, trait, x, y, 1)

def randomCards(group=table, x=0, y=0):
	quantity = [ "One", "Two", "Three", "Four", "Five", "Six" ]
	choice = askChoice("How many?", quantity)
	if choice <= 0:
		return
	isHidden = askChoice("Hide cards?",["Yes", "No"])
	pile, trait = cardTypePile()
	if pile is None: return
	if pile.controller != me:
		if isHidden == 1:
			remoteCall(pile.controller, "randomCardN", [me, pile, trait, x, y, choice, True])
		else:
			remoteCall(pile.controller, "randomCardN", [me, pile, trait, x, y, choice])
	else:
		if isHidden == 1:
			randomCardN(me, pile, trait, x, y, choice, True)
		else: 
			randomCardN(me, pile, trait, x, y, choice)

def summonScourge(group=table, x=0, y=0):
	scourges = [c.name for c in shared.piles['Scourge'] if c.Type == "Scourge"]
	scourgeList = list(set(scourges))
	scourgeList.append("Random Scourge")
	choice = askChoice("Which Scourge?", scourgeList)
	if choice <= 0:
		return
	if scourgeList[choice-1] == "Random Scourge":
		remoteCall(pile.controller, "randomCardN", [me, shared.piles['Scourge'], 0, x, y, 1])
	else:
		if shared.piles['Scourge'].controller != me:
			shared.piles['Scourge'].controller = me
		chosenScourge = findCardByName(shared.piles['Scourge'],scourgeList[choice-1])
		if chosenScourge == None:
			whisper("Could not find chosen scourge card {}. No scourge with that name.".format(scourgeList[choice]))
			return
		chosenScourge.moveToTable(x,y)
			
def buildNewLocation(group=table, x=0, y=0):
	scenario = findScenario(table)
	locName = askString("Please enter the location name.","Loc")
	if locName == None: 
		whisper("You did not enter a location name. No location was built.")
		return
	else:
		location = findCardByName(shared.piles['Location'],locName)
		if location == None:
			whisper("Could not find location {}. No location was built.".format(locName))
			return
		else:
			cards = [ c for c in table if c.Type == "Location" ]
			numLocs = len(cards)
			locNum = numLocs + 1
			buildLocation(scenario,location,shared.piles['Location{}'.format(locNum)])
			location.moveToTable(x,y)
			whisper("{} was built as location {}.".format(locName,locNum))
			
def hasTrait(card, trait):
	if card is None:
		return False
	if trait == "Any":
		return True
	if trait == "Non-Basic":
		return "Basic" not in card.Traits.splitlines()
	if trait == "Non-Basic, Non-Elite":
		return "Basic" not in card.Traits.splitlines() and "Elite" not in card.Traits.splitlines()
	if card.Traits is None or len(card.Traits) == 0:
		return False
	return trait in card.Traits.splitlines()
	
def randomCardN(who, pile, trait, x, y, n, hide=False):
	mute()
	if y > 0:
		y -= 50
	cards = [ c for c in pile if hasTrait(c, trait) ]
	while n > 0 and len(cards) > 0:
		card = cards[int(random()*len(cards))]
		cards.remove(card)
		card.moveToTable(x, y, hide)
		if who != me:
			card.setController(who)
		x = x + 10
		n -= 1	

def cardTypePile():
	mute()
	types = ["Henchman", "Monster", "Barrier", "Armor", "Weapon", "Spell", "Item", "Ally", "Blessing", "Scourge", "Ship"]
	choice = askChoice("Pick card type", types)
	if choice <= 0:
		return None, None	
	pile = shared.piles[types[choice-1]]
	
	# Ask for an optional trait
	traits = [ ]	
	for c in pile:
		for t in c.Traits.splitlines():
			if t != "and" and t not in traits:
				traits.append(t)
	traits.sort()

	inserted=1
	traits.insert(0, "Any")

	if "Basic" in traits:
		traits.insert(1, "Non-Basic")
		inserted += 1
		if "Elite" in traits:
			traits.insert(2, "Non-Basic, Non-Elite")
			inserted += 1
	choice = 1
	if len(traits) > inserted:
		choice = askChoice("Pick a trait", traits)
		if choice <= 0:
			choice = 1
	return pile, traits[choice-1]
	
#---------------------------------------------------------------------------
# Menu items - called to see if a menu item should be shown
#---------------------------------------------------------------------------
def isPile(cards, x=0, y=0):
	for c in cards:
		if c.pile() is None:
			return False
	return True
	
def isMythPath(cards, x=0, y=0):
	for c in cards:
		if c.Subtype != 'Mythic Path':
			return False
	return True

def isLocation(cards, x=0, y=0):
	for c in cards:
		if c.Type != 'Location':
			return False
	return True

def isVillain(cards, x=0, y=0):
	for c in cards:
		if c.Subtype != 'Villain':
			return False
	return True

def isShip(cards, x=0, y=0):
	for c in cards:
		if c.Type != 'Ship':
			return False
	return True

def isEnemyShip(cards, x=0, y=0):
	for c in cards:
		if c.type != 'Ship' or c.pile() == shared.piles['Plunder']:
			return False
	return True

def isWrecked(cards, x=0, y=0):
	for c in cards:
		if c.Type != 'Ship' or c.alternate != "B":
			return False
	return True
	
def isNotWrecked(cards, x=0, y=0):
	for c in cards:
		if c.Type != 'Ship' or c.alternate == "B":
			return False
	return True

def hasPlunder(cards,x=0, y=0):
	for c in cards:
		if c.Type != 'Ship' or c.pile() is None or len(c.pile()) == 0:
			return False
	return True

def isBoon(cards, x=0, y=0):
	for c in cards:
		if c.Type != 'Boon':
			return False
	return True
	
def isBoxed(cards, x=0, y=0):
	for c in cards:
		if c.Type not in ('Boon', 'Bane', 'Feat', 'Ship', 'Scourge', 'Support'):
			return False
	return True
	
def hasDice(cards, x=0, y=0):
	for c in cards:
		count = 0
		for die in [ d20, d12, d10, d8, d6, d4 ]:
			count += c.markers[die]
		if count == 0:
			return False
	return True
	
def hasMythCharges(card, x=0, y=0):
	if card.markers[mythicCharge] > 0:
		return True
	return False

def usePlunder(groups, x=0, y=0):
	#Check to see if the group contains a ship
	for g in groups:
		for c in g:
			if c.Type == 'Ship':
				return True
	return False
	
#---------------------------------------------------------------------------
# Table card actions
#---------------------------------------------------------------------------
def exploreLocation(card, x=0, y=0):
	mute()
	if card.type != 'Location':
		whisper("This is not a location ....")
		return
	#Ensure all locations that were temporarily closed are re-opened
	for c in table:
		if c.Type == 'Location' and c.orientation != Rot0:
			c.orientation = Rot0
			
	notify("{} explores '{}'".format(me, card))
	pile = card.pile()
	if pile is None:
		whisper("Nothing to see here")
		return
	if len(pile) == 0:
		whisper("Location is fully explored")
		return
	x, y = card.position
	pile.top().moveToTable(x, y+14)
	
def defaultAction(card, x = 0, y = 0):
	mute()

	if rollDice(card): # If it has dice on - roll them
		clearTargets()
		return
	if card.Type == 'Ship':
		if card.pile() is None: # Another ship - Seize it
			seizeShip(card)
		else: # Our ship - either wreck or repair it
			flipCard(card, x, y)
	elif card.pile() is not None and card.pile() == shared.piles['Blessing Deck']: # Reveal the next blessing
		advanceBlessingDeck()
	elif card.pile() is not None and (card.Type == 'Location' or len(card.pile()) > 0):
		if card.Type == 'Location': # Explore location
			if len(card.pile()) > 0:
				exploreLocation(card)
			elif isOpen(card):
				closePermanently(card)
		else:
			t = card.pile().top()
			x, y = card.position
			t.moveToTable(x, y+14)
			notify("{} reveals {}".format(me, t))
	elif card.Subtype == 'Villain':
		hideVillain(card)
	elif card.Type == 'Bane': # Assume it is undefeated and shuffle back into location
		shuffleCard(card)
	elif card.Type == 'Boon': # Assume it is acquired
		acquireCard(card)
	else:
		flipCard(card, x, y)

def donateDice(card, x=0, y=0):
	# Move any dice on this card to the card targeted by me
	# If there is no target, default to the avatar of the active player
	# The actual dice movement is handled by the event callout when a card is targeted
	t = [ c for c in table if c.targetedBy is not None and c.targetedBy == me ]
	if len(t) == 0:
		t = [ c for c in table if c.Type == 'Character' and c.Subtype == 'Token' and c.highlight is not None ]

	if len(t) != 1:
		whisper("Unsure where to donate dice: target one card and try again")
	elif t[0] == card:
		whisper("You cannot donate dice to yourself")
	else:
		card.arrow(t[0]) # This triggers a callback (passDice)
				
def flipCard(card, x = 0, y = 0):
	mute()
	if card.Subtype == 'Token': return
	
	if card.alternates is not None and "B" in card.alternates:
		if card.alternate == "B":
			card.switchTo("")
		else:
			card.switchTo("B")
		debug("{} flips '{}'".format(me, card))
	elif card.isFaceUp:
		card.isFaceUp = False
		debug("{} turns '{}' face down.".format(me, card))        
	else:
		card.isFaceUp = True
		debug("{} turns '{}' face up.".format(me, card))   

def addToken(card, tokenType):
	mute()
	card.markers[tokenType] += 1

def subToken(card, tokenType):
    mute()
    card.markers[tokenType] -= 1
		
def tokens(card, num):
	mute()
	total = card.markers[plus] - card.markers[minus] + num
	if total > 0:
		card.markers[plus] = total
		card.markers[minus] = 0
	else:
		card.markers[minus] = -total
		card.markers[plus] = 0
		
def revealCard(card, x=0, y=0):
	mute()
	notify("{} reveals '{}'".format(me, card))
	
def rechargeCard(card, x=0, y=0):
	mute()
	notify("{} recharges '{}'".format(me, card))
	card.moveToBottom(me.deck)
	
def displayCard(card, x=0, y=0):
	mute()
	notify("{} displays '{}'".format(me, card))

def acquireCard(card, x=0, y=0):
	mute()
	card.moveTo(me.hand)
	notify("{} acquires '{}'".format(me, card))
	
def banishCard(card, x=0, y=0): #Move to correct pile in box
	mute()
	
	if card.Subtype == 'Villain': # This is probably not what the player wanted to do
		hideVillain(card, x, y, True)
		return
	
	if not isBoxed([card]):
		return
	
	if card.pile() == shared.piles['Blessing Deck']:
		if confirm("Are you sure?") != True: # This is unusual
			return
		card = shared.piles['Blessing Discard'].top()
		card.link(None)
		
	removeBasic = (getGlobalVariable("Remove Basic") == "1")
	removeElite = (getGlobalVariable("Remove Elite") == "1")
	remove = ((removeBasic and hasTrait(card, "Basic")) or (removeElite and hasTrait(card, "Elite")))

	if remove and ((card.Type == 'Boon' and confirm("Remove {} from box?".format(card.Name)) == True) or card.Type == 'Bane'):
		removeCard(card)
	else:
		notify("{} banishes '{}'".format(me, card))
		returnToBox(card)
		
def buryCard(card, x=0, y=0): #Move to bury pile
	mute()
	notify("{} buries '{}'".format(me, card))
	card.moveTo(me.Buried)
	
def discardCard(card, x=0, y=0): #Move to discard pile
	mute()
	notify("{} discards '{}'".format(me, card))
	card.moveTo(me.Discarded)
	
def removeCard(card, x=0, y=0):
	mute()
	notify("{} removes '{}' from play".format(me, card))
	card.delete()

def shuffleCard(card, x=0, y=0):
	mute()
	pile = card.pile()
	if pile is None: # This is a normal card - if it is over a pile we shuffle it into the pile
		c = overPile(card)
		if c is None: return
		pile = c.pile()
		notify("{} moves '{}' into '{}' deck".format(me, card, pile.name))
		card.moveTo(pile)
	shuffle(pile)
	
def peekTop(card, x=0, y=0):
	mute()
	pile = card.pile()
	if pile is None or len(pile) == 0: return
	notify("{} looks at the top card of the '{}' deck".format(me, card))
	src = pile.top()
	src.peek() # This doesn't seem to reveal the card id as expected
	#Move the top card to a pile with full visibility
	if lockPile(shared.piles['Internal']):
		src.moveTo(shared.piles['Internal'])	
		whisper("{} looks at '{}'".format(me, src))
		src.moveTo(pile)
		unlockPile(shared.piles['Internal'])	

def peekTop2(card, x=0, y=0):
	peekTopN(card, 2)

def peekTop3(card, x=0, y=0):
	peekTopN(card, 3)

def peekTop5(card, x=0, y=0):
	peekTopN(card, 5)
	
def peekTopN(card, n):
	mute()
	pile = card.pile()
	if pile is None: return
	notify("{} looks at the top {} cards of the '{}' deck".format(me, n, card))
	pile.lookAt(n)
		
def peekBottom(card, x=0, y=0):
	mute()
	pile = card.pile()
	if pile is None: return
	notify("{} looks at the bottom card of the '{}' deck".format(me, card))
	src = pile.bottom()
	src.peek() # This doesn't seem to reveal the card id as expected
	#Move the bottom card to a pile with full visibility
	if lockPile(shared.piles['Internal']):
		src.moveTo(shared.piles['Internal'])	
		whisper("{} looks at '{}'".format(me, src))
		src.moveToBottom(pile)
		unlockPile(shared.piles['Internal'])
	
def peekBottom2(card, x=0, y=0):
	mute()
	pile = card.pile()
	if pile is None: return
	notify("{} looks at the bottom 2 cards of the '{}' deck".format(me, card))
	pile.lookAt(2, False)
	
def peekBottom3(card, x=0, y=0):
	mute()
	pile = card.pile()
	if pile is None: return
	notify("{} looks at the bottom 3 cards of the '{}' deck".format(me, card))
	pile.lookAt(3, False)

def pileMoveTB(card, x=0, y=0):
	mute()
	#Move the top card to the bottom
	pile = card.pile()
	if pile is None or len(pile) == 0: return
	notify("{} moves the top card of the '{}' pile to the bottom".format(me, card))
	c = pile.top()
	c.moveToBottom(pile)

def pileMoveBT(card, x=0, y=0):
	mute()
	#Move the bottom card to the top
	pile = card.pile()
	if pile is None or len(pile) == 0: return
	notify("{} moves the bottom card of the '{}' pile to the top".format(me, card))
	pile.bottom().moveTo(pile)
	
def pileSwap12(card, x=0, y=0):
	mute()
	pile = card.pile()
	if pile is None or len(pile) < 2: return
	notify("{} swaps to the top 2 cards of the '{}' pile".format(me, card))
	pile[1].moveTo(pile)

def findScenario(group):
	found = [s for s in group if s.Subtype == 'Scenario']
	if len(found) == 1:
		return found[0]
	return None
	
def findPath(group):
	found = [p for p in group if p.Subtype == 'Adventure Path']
	if len(found) == 1:
		return found[0]
	return None
	
# Returns a tuple closed, gameover	
def closePermanently(card, x=0, y=0):
	if closeLocation(card, True):
		scenario = findScenario(table)
		if scenario.Name in [ 'Scaling Mhar Massif' ,'Local Heroes', 'Sunken Treasure', 'Home Sweet Home', 'The Fall of Kenabres','1-1D Crusaders Assemble','The Big Bonfire','The Old Shipwreck','The Pharasmin Lottery','Panic in the Streets','Evening at the Canny Jackal']: # These scenarios are only won when the last location is closed
			open = [ c for c in table if isNotPermanentlyClosed(c) ]
			if len(open) == 0:
				if scenario.Name in ['1-1D Crusaders Assemble']: #In Crusaders Assemble, after you close the last location, build Laboratory
					foundLaboratory = False
					for card in table: 
						if card.Type == 'Location' and card.Name == 'Laboratory':
							foundLaboratory = True
					if foundLaboratory == True:
						gameOver(True)
						return True, True
					else:
						location = findCardByName(shared.piles['Location'],'Laboratory')
						newVillain = findCardByName(shared.piles['Villain'],'Ylyda Svyn')
						if location is None:
							whisper("Failed to find location Laboratory")
						else:
							# Count the number of locations on the table
							nl = 0 
							for card in table:
								if card.Type == 'Location':
									nl += 1
							pileName = "Location{}".format(nl+1)
							buildLocation(findScenario(table), location, shared.piles[pileName])
							if newVillain is None:
								whisper("Failed to find villain in the box")
							else:
								newVillain.moveTo(location.pile())
								shuffle(location.pile())
								location.moveToTable(LocationX(nl+1,nl+1), LocationY)
							whisper("{} builds location {}".format(me,location))
						return True, False
				if scenario.Name in ['The Old Shipwreck']:
					foundCabin = False
					openLoc = False
					for card in table:
						if card.Type == 'Location' and card.Name == "Ship's Cabin":
							foundCabin = True
						if card.Type == 'Location' and isOpen(card):
							openLoc = True
					if foundCabin == True and openLoc == False:
						gameOver(True)
						return True, True
					else:
						location = findCardByName(shared.piles['Location'],"Ship's Cabin")
						newVillain = findCardByName(shared.piles['Villain'],'Vorka')
						if location is None:
							whisper("Failed to find location Ship's Cabin")
						else:
							#Count the number of locations on the table
							nl = 0
							for card in table:
								if card.Type == 'Location':
									nl += 1
							pileName = "Location{}".format(nl+1)
							buildLocation(findScenario(table),location,shared.piles[pileName])
							if newVillain is None:
								whisper("Failed to find villain in the box")
							else:
								newVillain.moveTo(location.pile())
								numPlayers = len(getPlayers())
								i = 0
								while i < numPlayers:
									newMonster = shared.piles['Monster'].random()
									newMonster.moveTo(location.pile())
									i = i + 1
								shuffle(location.pile())
								location.moveToTable(LocationX(nl+1,nl+1), LocationY)
							whisper("{} builds location {}".format(me,location))
						return True, False
							
				else:	
					gameOver(True)
					return True, True
		return True, False
	return False, False

def closeTemporarily(card, x=0, y=0):
	scenario = findScenario(table)
	if scenario.Name in ('Desiccated Delirium'):
		whisper("Cannot temporarily close locations in this scenario.")
		return
	elif isOpen(card):
		closeLocation(card, False)
	
def hideVillain(villain, x=0, y=0, banish=False):
	mute()
	if villain.Subtype != 'Villain':
		notify("This is not a Villain ...")
		return
		
	#In Inside Lucrehold, Brinebones keeps going back to the blessing deck
	if villain.Name == 'Brinebones' and findScenario(table).Name == 'Inside Lucrehold':
		villain.moveTo(shared.piles['Blessing Deck'])
		shuffle(shared.piles['Blessing Deck'])
		advanceBlessingDeck()
		whisper("Brinebones is moved back into the Blessing Deck after advancing it.")
		return
	
	#In the Fifth Crusade, defeating Nulkineth causes a new location with Maugla to be created
	if villain.Name == 'Nulkineth' and findScenario(table).Name == 'The Fifth Crusade':
		location = overPile(villain, True)
		returnToBox(villain)
		if isOpen(location): # Ensure location is closed
			closed, done = closePermanently(location)
		maugla = findCardByName(shared.piles['Villain'],"Maugla")
		if maugla is not None:
			locs = [c for c in table if c.Type == 'Location']
			randIndex = int(random()*len(locs))
			randLoc = locs[randIndex]
			maugla.moveTo(randLoc.pile())
			if not isOpen(randLoc):
				flipCard(randLoc)
			shuffle(randLoc.pile())
			return
	#In Audience with the Inheritor, Lady of Valor goes back into the blessings deck unless you choose to win
	elif villain.Name == 'Lady of Valor' and findScenario(table).Name == 'Audience with the Inheritor':
		choices = ("Yes","No")
		win = askChoice("Would you like to win the game?",choices)
		if win == 1:
			gameOver(True)
			return
		else:
			villain.moveTo(shared.piles['Blessing Deck'])
			shuffle(shared.piles['Blessing Deck'])
			advanceBlessingDeck()
			whisper("Lady of Valor was shuffled into the blessings deck.")
			return
	
	choices = [ 'Evaded', 'Defeated', 'Undefeated' ]
	if banish:
		choices.append('Banished')
	choice = askChoice("Was the villain ....", choices)
	if choice is None or choice == 0:
		return
	
	if villain.pile() is not None:
		villain.link(None)
		
	if choices[choice-1] == 'Evaded':
		shuffleCard(villain, x, y)
		return
				
	if choices[choice-1] == 'Banished':	
		notify("{} banishes '{}'".format(me, villain))
		returnToBox(villain)
		return
	
	if choices[choice-1] == 'Undefeated': #handle any villain-specific undefeated conditions
		if villain.Name == 'Karsos':
			maze = findCardByName(shared.piles['Location'],"Maze")
			if maze is not None:
				# Count the number of locations on the table
				nl = 0 
				for card in table:
					if card.Type == 'Location':
						nl += 1
				pileName = "Location{}".format(nl+1)
				buildLocation(findScenario(table),maze,shared.piles[pileName])
				maze.moveToTable(LocationX(nl+1,nl+1), LocationY)
				whisper("{} builds the Maze and must move there.".format(me))
			else:
				whisper("Could not find location Maze... Maze was not built!")
	
	# We need to hide the villain in an open location
	defeated = choices[choice-1] == 'Defeated'		
	blessing = shared.piles['Blessing'] if defeated else shared.piles['Blessing Deck']		
	location = overPile(villain, True) #Determine the location of the Villain (based on whether it is over a pile on the table)
	closed = False
	
	if defeated: # Normally we close the location the villain came from
		if findScenario(table).Name == '0-1F The Treasure of Jemma Redclaw' and villain.Name == 'Jemma Redclaw':
			gameOver(True)
		elif villain.Name == 'The Matron':
			notify("{} banishes '{}'".format(me, villain))
			returnToBox(villain)
			krelloort = findCardByName(shared.piles['Villain'],'Krelloort')
			krelloort.moveTo(location.pile())
			shuffle(location.pile())
			notify("{} shuffles Krelloort into {}".format(me, location))
			return
		elif villain.Name == 'Vellexia' and findScenario(table).Name == "Nocticula's Attention":
			shuffleCard(villain,x,y)
			blessingNocticula = findCardByName(shared.piles['Loot'],"Blessing of Nocticula")
			if blessingNocticula is not None:
				blessingNocticula.moveToTable(PlayerX(-4),StoryY)
			else:
				notify("Not enough Blessings of Nocticula to display!")
			nocticula = eval(getGlobalVariable('nocticula'))
			nocticula = nocticula + 1
			if len(getPlayers()) <= nocticula:
				gameOver(True) #If the number of blessings of Nocticula equals the number of players, you win!
			setGlobalVariable('nocticula',nocticula)
			return
		if location is None or location.Type != 'Location': # Not sure which location to close
			if not confirm("Did you close the location?"):
				whisper("Close the location manually, then hide the villain")
				return
			closed = True
		elif isOpen(location): # Ensure location is closed
			closed, done = closePermanently(location) # If Villain(s) found in pile game is not over
			if done:
				return

	#If there are no open locations the villain has been cornered
	open = [ card for card in table if isOpen(card) ]
	for c in open:
		if c.Name in ('Abyssal Rift','Gate of the Worldwound'):
			open.remove(c)
			closed = True
	if len(open) == 0:
		returnToBox(villain)
		#In the Secret of Mancatcher Cove and Vengeance at Sundered Crag, if you defeat the main villain, build a new location and bring in another villain
		if villain.Name in ['Thurl and Inhaz','Isabella "Inkskin" Locke'] and findScenario(table).Name in ['The Secret of Mancatcher Cove','Vengeance at Sundered Crag']:
			location = None
			newVillain = None
			if findScenario(table).Name == 'Vengeance at Sundered Crag':
				location = findCardByName(shared.piles['Location'],'Watchtower')
				newVillain = findCardByName(shared.piles['Villain'],'Tancred Desimire')
			else:
				location = findCardByName(shared.piles['Location'],'Mancatcher Cove')
				newVillain = findCardByName(shared.piles['Villain'],'The Matron')
			if location is None:
				whisper("Failed to find location {}".format(location.Name))
			else:
				# Count the number of locations on the table
				nl = 0 
				for card in table:
					if card.Type == 'Location':
						nl += 1
				pileName = "Location{}".format(nl+1)
				buildLocation(findScenario(table), location, shared.piles[pileName])
				if newVillain is None:
					whisper("Failed to find villain in the box")
				else:
					newVillain.moveTo(location.pile())
				shuffle(location.pile())
				location.moveToTable(LocationX(nl+1,nl+1), LocationY)
				whisper("{} builds location {}".format(me,location))
			notify("{} banishes '{}'".format(me, villain))
			returnToBox(villain)
		#In Redeeming the Herald, give the player the option to summon and defeat Baphomet
		elif findScenario(table).Name == 'Redeeming the Herald' and villain.Name == 'Corrupted Herald':
			choices = ("I WILL DESTROY HIM!","NO WAY!")
			choice = askChoice("Would you like to attempt to kill Baphomet?",choices)
			if choice == 1:
				baphomet = findCardByName(shared.piles['Villain'],"Baphomet")
				baphomet.moveToTable(PlayerX(-1),StoryY)
				whisper("You have challenged the Demon Lord Baphomet! FEAR HIM!")
				return
			elif choice == 2:
				gameOver(true)
				return
		#In Shore Leave at Port Peril, pull out the Pirate Council and don't end the game yet.
		elif findScenario(table).Name == 'Shore Leave at Port Peril' and villain.Name == 'Caulky Tarroon':
			# Count the number of locations on the table
			nl = 0 
			for card in table:
				if card.Type == 'Location':
					nl += 1
			pirateCouncil = findCardByName(shared.piles['Villain'],'The Pirate Council')
			pirateCouncil.moveToTable(LocationX(nl+1,nl+1), LocationY)
			whisper("If you defeat The Pirate Council, you earn the Letter of Marque!")
		elif villain.Name == 'Master Scourge' and findScenario(table).Name == '0-2A Love\'s Labours Lost': 
			location = findCardByName(shared.piles['Location'],'Tidewater Rock')
			if location is None:
				whisper("Failed to find location Tidewater Rock")
			else:
				players = len(getPlayers())
				nl = 0
				for card in table:
					if card.Type == 'Location':
						nl += 1
				pileName = "Location{}".format(nl+1)
				location.moveToTable(LocationX(nl+1,nl+1), LocationY)
				whisper("{} builds location {} with special card list".format(me,location))
				henchmen = ('Knuckles Grype', 'Slippery Syl Lonegan', 'Owlbear Heartshorn', 'Jaundiced Jape', 'Maheem', 'Aretta Bansion')
				for i in players:
					currHench = henchmen.random()
					addHench = findCardByName(shared.piles['Henchman'],currHench)
					addHench.moveTo(location.pile())
					henchmen.remove(currHench)
				shuffle(location.pile())
				ladyAgasta = findCardByName(shared.piles['Loot'],'Lady Agasta Smythee')
				ladyAgasts.moveToBottom(location.pile())
			notify("{} banishes '{}'".format(me,villain))
			returnToBox(villain)
		elif closed and villain.Name != 'Kelizar the Brine Dragon': # Defeating this villain (Sunken Treasure) doesn't end the game
			if findScenario(table).Name == 'Shore Leave at Port Peril' and villain.Name == 'The Pirate Council':
				nl = 0
				for card in table:
					if card.Type == 'Location':
						nl += 1
				marqueLetter = findCardByName(shared.piles['Loot'],'Letter of Marque')
				marqueLetter.moveToTable(LocationX(nl+1,nl+1),LocationY)
				whisper("You've earned the Letter of Marque!")
			gameOver(True)
		else:
			notify("{} returns {} to the box".format(me, villain))
		return

	# The villain has escaped
	debug("Villain has {} open locations".format(len(open)))
	hidden = shared.piles['Internal']
	if not lockPile(hidden):
		return	
	villain.moveTo(hidden)
	#Add a Blessing for each other open location
	for i in range(len(open)-1):
		card = blessing.random()
		if card is not None:
			card.moveTo(hidden)

	for loc in open:
		pile = loc.pile()
		card = hidden.random()
		if card is not None:			
			card.moveTo(pile)
		shuffle(pile)
		
	unlockPile(hidden)
	
	# Re-open temporarily closed locations
	for card in table:
		if card.Type == 'Location' and card.orientation != Rot0:
			card.orientation = Rot0

def seizeShip(ship, x=0, y=0):
	x,y = ship.position
	# Look for any current ship(s) and return to the box
	for c in table:
		if c.Type == 'Ship' and c.pile() == shared.piles['Plunder']:
			c.link(None)
			x, y = c.position
			returnToBox(c)
	ship.link(shared.piles['Plunder'])
	ship.moveToTable(x, y)
	ship.sendToBack()
	
def addToFleet(ship, x=0, y=0):
	fleet = eval(getGlobalVariable('Fleet'))
	if ship.Name in fleet:
		whisper("{} is already in your fleet".format(ship))
		return
	fleet.append(ship.Name)
	setGlobalVariable('Fleet', str(fleet))
	
def addRandomPlunder(ship, x=0, y=0):
	addPlunder(ship)
	
def addChosenPlunder(ship, x=0, y=0):
	addPlunder(ship, 'Choose')
	
def addWeaponPlunder (ship, x=0, y=0):
	addPlunder(ship, 'Weapon')

def addArmorPlunder (ship, x=0, y=0):
	addPlunder(ship, 'Armor')
	
def addSpellPlunder (ship, x=0, y=0):
	addPlunder(ship, 'Spell')

def addAllyPlunder (ship, x=0, y=0):
	addPlunder(ship, 'Ally')
	
def addItemPlunder (ship, x=0, y=0):
	addPlunder(ship, 'Item')

def addPlunder(ship, type='Roll'):
	mute()
	
	if type == 'Roll':
		roll = int(random()*6) # Roll on the plunder table
		if roll >= 5: # User choice
			type = 'Choose'
		else:
			type = plunderTypes[roll]

	if type == 'Choose':
		options = plunderTypes
	else:
		options = [ type ]
		
	if len(options) > 1:
		choice = askChoice("Plunder Type", options)
		if choice is None or choice == 0:
			return
		choice -= 1
	else:
		choice = 0
	notify("{} adds {} to {}".format(me, options[choice], ship))
	shared.piles[options[choice]].random().moveTo(ship.pile())
	
def banishRandomPlunder(ship, x=0, y=0):
	mute()
	card = ship.pile().random()
	card.moveTo(shared.piles['Internal']) # Ensure the card is in a pile with full visibility so we know where to put it
	banishCard(card)
	
#---------------------------------------------------------------------------
# Pile Group Actions
#---------------------------------------------------------------------------
	
def rechargeRandom(group, x=0, y=0): # Discarded pile
	mute()
	if len(group) == 0: return
	card = group.random()
	notify("{} recharges '{}'".format(me, card))
	card.moveToBottom(me.deck)

def buryRandom(group, x=0, y=0): # Discarded pile
	mute()
	if len(group) == 0: return
	card = group.random()
	notify("{} buries '{}'".format(me, card))
	card.moveTo(me.Buried)

def discardRandom(group, x=0, y=0): # Hand
	mute()
	if len(group) == 0: return
	card = group.random()
	notify("{} discards '{}'".format(me, card))
	card.moveTo(me.Discarded)
	
def returnToBlessingDeck(group, x=0, y=0): # Blessing Discard
	mute()
	if len(group) == 0:
		notify("No cards to return")
		return
	destination = shared.piles['Blessing Deck']
	group.random().moveTo(destination, int(random()*(1+len(destination))))
	notify("{} returns a card to the Blessing Deck".format(me))

def revealRandom(group, x=0, y=0): # Most shared piles use this
	if len(group) == 0: return
	group.random().moveToTable(x, y)
	
def shufflePile(group, x=0, y=0): # Most piles use this
	mute()
	if len(group) == 0: return
	shuffle(group)
	
#---------------------------------------------------------------------------
# Hand Group Actions
#---------------------------------------------------------------------------

def drawUp(group): # group == me.hand
	mute()
	handSize = getHandSize()
	if len(group) > handSize:
		notify("{} already has too many cards ({}), max {}".format(me, len(group), handSize))
		return
	
	toDraw = handSize - len(group)
	for c in me.deck.top(toDraw):
		c.moveTo(group)
	
	if len(group) < handSize: #We ran out of cards ... and died
		eliminated(me, True)
		notify("{} has run out of cards".format(me))
	elif toDraw == 1:
		notify("{} draws a card".format(me))
	elif toDraw > 0:
		notify("{} draws {} cards".format(me, toDraw))

#---------------------------------------------------------------------------
# Deck Group Actions
#---------------------------------------------------------------------------

def drawCard(group, x=0, y=0): # me.deck
	mute()
	card = group.top()
	if card is None:
		return	
	card.moveTo(me.hand)
	notify("{} draws '{}'".format(me, card))
	
#---------------------------------------------------------------------------
# Game logic and set up
#---------------------------------------------------------------------------
def playerSetup():
	id = me._id
	debug("Player {}: Setup ....".format(id))
	
	sync() # Make sure all other processing is complete
	inUse(me.Discarded) #Remove all the loaded player cards from the box (shared piles)
	
	handSize = 4
	favoured = []
	cohort = None
	charName = None
	cardTypes = [ 'Weapon', 'Spell', 'Armor', 'Item', 'Ally', 'Blessing' ]
	minC = { 'Weapon':0, 'Spell':0, 'Armor':0, 'Item':0, 'Ally':0, 'Blessing':0 }
	maxC = { 'Weapon':0, 'Spell':0, 'Armor':0, 'Item':0, 'Ally':0, 'Blessing':0 }
	custom = False
	
	#Move Character Card to the table
	for card in me.hand:
		if card.Type == 'Character':
			if card.Subtype == 'Mythic Path':
				card.moveToTable(PlayerX(id),StoryY)
			elif card.Subtype != 'Token': # Extract information about the hand size and favoured card type
				custom = card.Name == 'Custom'
				if len(card.Attr3) > 0 and card.Attr3 != 'None':
					#some characters have strange favored cards, they will be dealt with elsewhere
					if card.Attr3.startswith('Special'):
						favoured = card.Attr3.split(':')
						favoured[1] = card.Name
					else:
						favoured = card.Attr3.split(' or ')
						debug("Favoured = {}".format(favoured))
				if len(card.Attr4) > 0:
					cohort = card.Attr4.replace('Cohort: ','')
				#Store Card name because some characters are weird
				charName = card.Name
				#Store Card counts
				for line in card.Attr2.splitlines():
					type, rest = line.split(':',1)
					counts = rest.split()
					minC[type] = num(counts[0])
					maxC[type] = num(counts[len(counts)-1])
				card.moveToTable(PlayerX(id), StoryY)
				update()
				flipCard(card)
				if len(card.Attr3) > 0:
					handSize = num(card.Attr3[0])
					debug("Hand Size = {}".format(handSize))
				notify("{} places {} on the table".format(me, card))
		elif card.Subtype == 'Cohort':
			returnToBox(card)
		else:
			whisper("Unexpected card '{}' loaded into hand".format(card))
	
	#Process feats - these override default values extracted from basic character sheet
	debug("Processing feats ....")
	for card in me.Buried:
		if card.Name[:9] == "Hand Size":
			handSize = num(card.Name[10:])
			debug("HandSize override - {}".format(handSize))			
		elif card.Subtype == 'Favoured':
			favoured.append(card.Name)
			debug("Favoured added - {}".format(favoured))
		elif card.Subtype == 'Card':
			type, count = card.Name.split()
			minC[type] = num(count)
	
	#Check loaded deck matches expected card distribution. Add missing Card feats if required
	hexmap = [ '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'a', 'b', 'c', 'd', 'e', 'f' ]
	counts = { 'Weapon':0, 'Spell':0, 'Armor':0, 'Item':0, 'Ally':0, 'Blessing':0 }
	for c in me.Discarded:
		if c.Subtype == 'Loot':
			type = c.Subtype2
		elif c.Subtype in ('Weapon','Spell','Armor') and charName == 'Mavaro':
			type = 'Item'
		else:
			type = c.Subtype
		counts[type] += 1
		
	i = 0
	dist=""
	if charName in ('Mavaro','Ezren'):
		notify("You're using a character with a strange way of building his or her deck. Card counts will not be verified!")
	else:
		for type in cardTypes:
			dist = dist + "{}:{} ".format(type, counts[type])
			if counts[type] > maxC[type] and not custom:
				notify("{} has more '{}' cards than allowed".format(me, type))
			if counts[type] < minC[type]:
				whisper("You don't have enough '{}' cards in your deck. Found {}, expected {}".format(type, counts[type], minC[type]))
			elif counts[type] > minC[type]:
				whisper("You have more '{}' cards than expected - updating your card feat to {}".format(type, counts[type]))
				#Delete the current card feat (if any)
				for c in me.Buried:
					if c.Type == 'Feat' and c.Subtype == 'Card' and type in card.Name:
						c.delete()
				id = '7c5d69b1-b5ec-47f2-ba25-5a839291c3' + hexmap[i] + hexmap[counts[type]]
				table.create(id, 0, 0, 1, True).moveTo(me.Buried)
			i += 1	
	
	storeHandSize(handSize)
	storeFavoured(favoured)
	storeCohort(cohort)
	storeCards(dist)
	eliminated(me, False)
	debug("HandSize {}, Favoured type {}".format(handSize, favoured))
	whisper("Drag avatar to your starting location once the scenario is set up")
	
#Set up the scenario
#Move each location to the table and create its deck
#Create the Blessing deck and reveal the top card
#If the scenario mentions an anchorage - return the location card to anchor the ship at
def scenarioSetup(card):
	mute()
	
	card.link(shared.piles['Scenario'])
	hidden = shared.piles['Internal']
	if not lockPile(hidden): return None
	
	scenarioSpecific = {}
	attr2Lines = card.attr2.splitlines()
	
	scenarioSpecific['anchorage'] = None # This is set to the location card if an anchorage is mentioned in attr2 of the scenario.
	if 'Your ship is anchored at ' in card.attr2:
		for l in attr2Lines:
			if 'Your ship is anchored at ' in l:
				shipSearch = card.attr2.replace('Your ship is anchored at ','').replace('the ','')
	else:
		shipSearch = ''
	scenarioSpecific['cohortNum'] = 0
	if 'Cohort' in card.attr2:
		for l in attr2Lines:
			if 'Cohort' in l:
				j = 1
				for c in l.replace('Cohort: ','').replace('Cohorts: ','').split(', '):
					scenarioSpecific['cohort{}'.format(j)] = str(c)
					j = j+1
				scenarioSpecific['cohortNum'] = j-1
	scenarioSpecific['troopName'] = ''
	if 'Display the troop' in card.attr2:
		for l in attr2Lines:
			if 'Display the troop' in l:
				troopName = l.replace('Display the troop ','').replace('.','')
				scenarioSpecific['troopName'] = troopName
				
	scenarioSpecific['siegeDeck'] = False #This is to set the Siege Deck mechanic for certain scenarios in Mummy's Mask.
	if card.Name in ('Pride of the Dispossessed'):
		scenarioSpecific['siegeDeck'] = True
		storeSiege(True)
		defensiveStance = findCardByName(shared.piles['Support'], "Defensive Stance")
		if defensiveStance is None:
			whisper("Failed to find Defensive Stance in Support deck.")
		else:
			defensiveStance.moveToTable(PlayerX(-1)+30,StoryY)
			defensiveStance.link(shared.piles['Special'])
		
	locations = card.Attr1.splitlines()
	nl = numLocations()
	leaveSpace = 0 # We need to leave a space for 1 more location in some scenarios
	if card.Name in ('Rimeskull','The Free Captains\' Regatta'):
		nl = 8
	elif card.Name in ('Audience with the Inheritor'):
		nl = 6
	elif card.Name in ('Into the Runeforge','Isle of the Black Tower',"The Demon's Redoubt",'Onslaught on Drezen','0-6B The Battle of Abendego','The Tainted Tower', 'Chains of Silver'):
		nl -= 1
	elif card.Name in ['Scaling Mhar Massif','The Pleasure Center','0-6E Into the Maelstrom']:
		nl -= 2
	elif card.Name in ['Press Ganged!','Justifiable Deicide','0-6F Lost in the Storm','The Big Bonfire']:
		nl = 1
	elif card.Name in ['The Toll of the Bell','The Old Shipwreck']:
		nl = 2
	elif card.Name in ('Best Served Cold','Islands of the Damned'):
		nl += 1
	elif card.Name in ('The Secret of Mancatcher Cove','0-1B The Lone Shark','Home Sweet Home','Vengeance at Sundered Crag'):
		nl -= 1
		leaveSpace = 1
	elif card.Name in ('Demondome','1-1D Crusaders Assemble'):
		nl -= 2
		leaveSpace = 1
	elif card.Name in ('The Siege of Drezen', "Muminofrah's Amusement"):
		nl = 1
		leaveSpace = 1
		
	if nl < 1:
		nl = 1
	if nl > len(locations):
		nl = len(locations)
	for i in range(nl):
		debug("Processing Location '{}'".format(locations[i]))
		location = findCardByName(shared.piles['Location'], locations[i])
		if location is None:
			whisper("Failed to find location {}".format(locations[i]))
		else:
			pileName = "Location{}".format(i+1)
			buildLocation(card, location, shared.piles[pileName])
			location.moveToTable(LocationX(i+1, nl+leaveSpace), LocationY)
			if location.Name in shipSearch:
				scenarioSpecific['anchorage'] = location
			if location.Name == 'The Leng Device':
				location.markers[timer] = 12
			
	#Put the Villain and henchmen in a new pile, then shuffle and deal out to the locations
	flipCard(card) # Villain info is on Side B
	villain = None	
	if len(card.Attr2) > 0 and card.Attr2 != 'None':
		for v in card.Attr2.splitlines():
			villain = findCardByName(shared.piles['Villain'], v)
			if villain is None:
				whisper("Setup error: failed to find '{}'".format(v))
			else:
				if scenarioSpecific['siegeDeck'] == True:
					debug("Moving '{}' to siege deck".format(villain))
					villain.moveTo(shared.piles['Scenario'])
				else:
					debug("Moving '{}' to hidden pile".format(villain))
					villain.moveTo(hidden)
					
	# Some adventures set the villain aside
	if villain is not None and card.Name in ('Here Comes the Flood', 'The Road through Xin-Shalast','The Lady\'s Favor'):
		villain.moveToTable(PlayerX(-4),StoryY)
		villain.link(shared.piles['Special'])

	#In Justifiable Deicide, Deskari goes on the bottom of the deck
	if card.Name == 'Justifiable Deicide':
		villain.moveTo(shared.piles['Special'])
	
	#In The Big Bonfire, add several barriers to the Licktoad Camp
	if card.Name == 'The Big Bonfire':
		licktoad = findCardByName(table,"Licktoad Camp")
		if licktoad is not None:
			eatSlugs = findCardByName(shared.piles['Barrier'],"Eat A Bag Of Slugs Real Quick")
			if eatSlugs is not None:
				eatSlugs.moveTo(licktoad.pile())
			hideClubbed = findCardByName(shared.piles['Barrier'],"Hide or Get Clubbed")
			if hideClubbed is not None:
				hideClubbed.moveTo(licktoad.pile())
			rustyBiter = findCardByName(shared.piles['Barrier'],"The Rusty Earbiter")
			if rustyBiter is not None:
				rustyBiter.moveTo(licktoad.pile())
			fermentedApples = findCardByName(shared.piles['Barrier'],"Eat the Fermented Apples")
			if fermentedApples is not None:
				fermentedApples.moveTo(licktoad.pile())
			squealy = findCardByName(shared.piles['Barrier'],"Dance with Squealy Nord")
			if squealy is not None:
				squealy.moveTo(licktoad.pile())
			playerNum = len(getPlayers())
			i = 0
			while i < playerNum:
				c = shared.piles['Barrier'].random()
				c.moveTo(licktoad.pile())
				i = i + 1
		
	
	#In Breaking the Dreamstone, pull out the special Role card
	if card.Name == 'Breaking the Dreamstone':
		bikendi = findCardByName(shared.piles['Story'],'Bikendi Otongu (Ghost Mage)')
		bikendi.moveToTable(PlayerX(-1)-15,StoryY)
		
	#In the Battle of Empty Eyes, pull out the Wormwood ship
	if card.Name == 'The Battle of Empty Eyes':
		wormwood = findCardByName(shared.piles['Ship'],'Wormwood')
		wormwood.moveToTable(PlayerX(-1)-15,StoryY)
	
	#In 'Give the Devil His Due', display two ships and place plunder under one of them
	if card.Name == 'Give the Devil His Due':
		seaChanty = findCardByName(shared.piles['Ship'],'Sea Chanty')
		seaChanty.moveToTable(PlayerX(-1)+15,StoryY)
		seaChanty.sendToBack()
		seaChanty.link(shared.piles['Special']) # We use a non-standard plunder pile for this ship
		while len(shared.piles['Special']) < 14 - nl:
			addPlunder(seaChanty)		
		devilsPallor = findCardByName(shared.piles['Ship'],'Devil\'s Pallor')
		devilsPallor.moveToTable(PlayerX(-1)+30,StoryY)
		devilsPallor.sendToBack()
	
	#In The Treasure of Jemma Redclaw, the first villain is set aside and added to the Blessings deck, then two villains are added to decks.
	if card.Name in ('0-1F The Treasure of Jemma Redclaw'):
		jemma = findCardByName(hidden,'Jemma Redclaw')
		i = 0
		while i < 10:
			shared.piles['Blessing'].random().moveTo(shared.piles['Blessing Deck'])
			i=i+1
		jemma.moveTo(shared.piles['Blessing Deck'])
	
	debug("Hide Henchmen '{}'".format(card.Attr3))
	henchmen = []
	if card.Name == 'The Toll of the Bell': #The Toll of the Bell puts half the henchmen (rounded up) into one deck and the rest in the other
		henchmen = card.Attr3.replace(' per Character', '').replace('1 ','').splitlines()
		cardsPerLocation = (1+len(getPlayers()))/2
		repeat = 1
	elif card.Name == 'Here Comes the Flood':
		henchmen = 'Nightbelly Boas'.split(',')
		cardsPerLocation = 1
		repeat = 1
	elif card.Name == 'Justifiable Deicide':
		cardsPerLocation = (len(players)*6)
		henchCards = [c for c in shared.piles['Henchman'] if c.Abr in ('5','6')]
		for m in henchCards:
			m.moveTo(shared.piles['Location15'])
		i = 0
		while i < cardsPerLocation:
			shared.piles['Location15'].random().moveTo(hidden)
			i = i + 1
		repeat = 1
	elif 'Per Location: ' in card.Attr3 or ' per location' in card.Attr3 or ' per Location' in card.Attr3: # Special instructions for this one
		henchmen = card.Attr3.replace('Per Location: ','').replace(' per Location', '').replace(' per location', '').replace('1 ','').replace('Random ','').split(', ')
		cardsPerLocation = len(henchmen)
		repeat = len(henchmen)		
	elif 'Random Monsters' in card.Attr3 or 'Random monsters' in card.Attr3 or 'random monsters' in card.Attr3:
		cardsPerLocation = 1
		hiddenLen = len(hidden)
		for i in range(nl-hiddenLen):
			shared.piles['Monster'].random().moveTo(hidden)
		repeat = 1
	elif card.Name == 'Press Ganged!': #For the Press Ganged! scenario, pull one random henchman from the pile and deal it into a new banes pile
		henchmen = card.Attr3.splitlines()
		randIndex = int(random()*len(henchmen))
		randHench = findCardByName(shared.piles['Henchman'], henchmen[randIndex])
		del henchmen[randIndex] #Remove the random henchman from our list - the remaining ones are added to the location
		cardsPerLocation = len(henchmen)+1
		repeat = 1
		# Move the Random henchman to the banes pile (this is our scenario pile) 
		randHench.moveTo(shared.piles['Scenario'])	
	elif card.Name == 'Death of the Storm King': #This scenario includes a cohort as a henchman, so that cohort is added to the hidden pile
		cardsPerLocation = 1
		henchmen = ('Flayed Man', 'Lord Stillborn', 'Abyssal Armys')
		suture = findCardByName(shared.piles['Cohort'],"The Suture")
		suture.moveTo(hidden)
		repeat = 1
		nl = nl - 1
	elif card.Name == 'Ahead of the Competition': #This scenario uses random allies as henchmen, so those are added to the hidden pile
		cardsPerLocation = 1
		repeat = 1
		numAllies = nl - 1
		for i in range(nl):
			shared.piles['Ally'].random().moveTo(hidden)
	else:
		henchmen = card.Attr3.splitlines()
		cardsPerLocation = 1
		repeat = 1
		if card.Name in ['Into the Eye','0-6F Lost in the Storm']:
			cardsPerLocation += len(getPlayers())
			if card.Name == '0-6F Lost in the Storm':
				cardsPerLocation += 1
	if card.Name == 'Isle of the Black Tower': #Isle of the Black Tower needs three extra henchmen
		nl = nl + 3
	index = 0
	while len(hidden) < nl * cardsPerLocation:
		if henchmen[index] in shared.piles: # A card type has been supplied
			man = shared.piles[henchmen[index]].random()
		else:
			man = findCardByName(shared.piles['Henchman'], henchmen[index])
			if man is None and henchmen[index][-1] == 's': # The last henchman entry might be pluralised - remove the trailing "s"
				man = findCardByName(shared.piles['Henchman'], henchmen[index][:-1])
		if man is None:
			whisper("Setup error: failed to find '{}'".format(henchmen[index]))
			if index == len(henchmen) - 1: # Stop a possible infinite loop if the final henchman is not loaded
				break;
		else:
			man.moveTo(hidden)
		index += 1
		if index == len(henchmen): #Repeat the last named entry if there are not enough named unique henchmen
			index -= repeat

	debug("Deal from hidden deck ...")
	
	#Now deal them to each location pile
	index = 0
	while len(hidden) > 0:
		if scenarioSpecific['siegeDeck'] == True:
			pile = shared.piles['Special']
		else:
			pile = shared.piles["Location{}".format(index+1)]
		for i in range(cardsPerLocation):
			if index == 0 and card.Name in ('Rimeskull', 'Into the Runeforge'):
				hidden.bottom().moveTo(pile) # Ensure Villain is in first location
			elif index == 0 and card.Name in ('Isle of the Black Tower'):
				m = 0
				while m < 4:
					hidden.bottom().moveTo(pile)
					m = m+1
			elif index == 1 and card.Name in ('Islands of the Damned'):
				m = 0 #ignore the Little Jaw location, useless declaration for space
			else:
				hidden.random().moveTo(pile)
		#In The Brine Banshee's Grave and Free Captain's Regatta, add an extra henchman to each location
		if card.Name in ("The Brine Banshee's Grave","The Free Captains' Regatta"):
			if card.Name == "The Brine Banshee's Grave":
				exHenchName = "Shipwreck"
			elif card.Name == "The Free Captains' Regatta":
				exHenchName = "Enemy Ship"
			extraHench = findCardByName(shared.piles['Henchman'],exHenchName)
			if extraHench is None:
				whisper("Could not find enough extra henchmen!")
			else:
				extraHench.moveTo(pile)
		shuffle(pile)
		index += 1
	unlockPile(hidden)
	
	if card.Name == 'Justifiable Deicide': #In this scenario, the villain ends up on the bottom of the only location deck
		deskari = findCardByName(shared.piles['Special'],"Deskari")
		if deskari is not None:
			deskari.moveToBottom(shared.piles['Location1'])
		else:
			deskari = findCardByName(shared.piles['Villain'],"Deskari")
			if deskari is not None:
				deskari.moveToBottom(shared.piles['Location1'])
			else:
				notify("Could not find the Villain!!")
	
	if card.Name == 'The Gibbering Swarm':
		locs = [c for c in table if c.Type == 'Location']
		for loc in locs:
			cardTypes = loc.Attr1.splitlines()
			if cardTypes is not None:
				details = cardTypes[0].split(' ')
				if details[0] == 'Monster':
					cards = num(details[1])
					for count in range(cards):
						c = shared.piles['Monster'].random()
						if c is None:
							whisper("No more {} cards to deal to location {}".format(details[0], loc))
							break
						c.moveTo(loc.pile())
	
	if card.Name == 'The Pleasure Center': #In this scenario, any henchmen left in the box are added to the Yearning House
		whisper("Moving the extra henchmen into the Yearning House deck.")
		yearning = findCardByName(table,"Yearning House")
		if yearning is not None:
			hench = findCardByName(shared.piles['Henchman'],"Sister Perversion")
			if hench is not None:
				hench.moveTo(yearning.pile())
			foundLast = 0
			while foundLast == 0:
				hench = findCardByName(shared.piles['Henchman'],"Pleaser")
				if hench is not None:
					hench.moveTo(yearning.pile())
				else:
					foundLast = 1
			shuffle(yearning.pile())

	if card.Name in ("Akhentepi's Legacy"): #In this scenario, an extra barrier with the Trap trait is shuffled into each location
		whisper("Adding extra barriers to locations.")
		locs = [c for c in table if c.Type == 'Location']
		for loc in locs:
			cardFound = False
			card = None
			while cardFound == False:
				card = localRandom(shared.piles['Barrier'])
				if "Trap" in card.Traits:
					cardFound = True
			if card is not None:
				card.moveTo(loc.pile())
			else:
				whisper("Failed to find barrer with the Trap trait!")
				return
	
	#If there is a siege deck, shuffle it
	if getSiege() == True:
		shuffle(shared.deck['Special'])
	
	# Perform scenario specific actions
	fn = cardFunctionName(card)
	if fn in globals():
		globals()[fn]('Setup')
		
	#Create the Blessing deck
	if card.Name != "Into the Eye":
		src = shared.piles['Blessing']
		dst = shared.piles['Blessing Deck']
		if card.Name == 'Sandpoint Under Siege':
			blessings = 25
		elif card.Name in ['Inside Lucrehold','The Fall of Kenabres']: #Villain is added to the deck
			blessings = 31
		elif card.Name == 'The Land of the Blind': #6 gholdakos are added to the deck
			blessings = 36
		elif card.Name == "Muminofrah's Amusement": #3 Cameltrops are added to the deck
			blessings = 33
		else:
			blessings = 30
		blessings += shared.ExtraBlessings
		if blessings < 0:
			blessings = 1
		while len(src) > 0 and len(dst) < blessings:
			src.random().moveTo(dst)
			
		if card.Name in ['Inside Lucrehold', 'The Fall of Kenabres', 'The Land of the Blind','The Feast of Spoils','Audience with the Inheritor',"Muminofrah's Amusement",'In Search of Chisisek']: #shuffle extra cards into the deck
			shuffle(dst)

	mythPaths = [ c for c in table if c.Subtype == 'Mythic Path']
	for m in mythPaths:
		if hasMythCharges(m):
			clearMythCharges(m)
		i = 0
		if card.Abr in ['1','2','3','4','5','6','7','8','9']:
			deckNum = int(card.Abr)
			if deckNum > 9 or deckNum is None:
				whisper("Could not determine correct number of mythic tokens. Please add manually.")
			else:
				while i < deckNum:
					mythicChargeAdd(m)
					i = i + 1
	
	notify("{} starts '{}'".format(me, card))
	return scenarioSpecific

	
#Create deck based on location distribution by moving random cards from the box to the location's pile
def buildLocation(scenario, location, locPile):
	debug("Processing Location '{}'".format(location))
	whisper("In buildLocation, getSiege is {}".format(getSiege())) #debugging
	cardTypes = location.Attr1.splitlines()
	if scenario.Name == 'Best Served Cold': #Best Served Cold replaces Allies with more Monsters at all locations
		entry = cardTypes[6]
		details = entry.split(' ')
		numAllies = 0
		if details[0] == 'Ally':
			numAllies = int(details[1])
		entry = cardTypes[0]
		details = entry.split(' ')
		numMonsters = 0
		if details[0] == 'Monster':
			numMonsters = int(details[1])
			numMonsters += numAllies
		cardTypes[0] = 'Monster '+str(numMonsters)
		cardTypes[6] = 'Ally 0'
	for entry in cardTypes:
		details = entry.split(' ') # i.e. Monster 3
		if len(details) == 2 and details[0] in shared.piles:
			debug("Adding {} cards of type {}".format(details[1], details[0]))
			pile = shared.piles[details[0]]
			cards = num(details[1])
			
			#Card specific rules
			if details[0] == 'Barrier' and scenario.Name == 'Press Ganged!':
				cards += 5
			if details[0] == 'Spell' and scenario.Name == 'The Black Tower':
				cards += 1
			if details[0] == 'Monster' and scenario.Name == 'The Gibbering Swarm':
				cards = 0
			if scenario.Name == 'The Toll of the Bell':
				if details[0] == 'Ally' and location.Name == 'Fog Bank':
					cards += 2*len(getPlayers())
				if details[0] == 'Monster' and location.Name == 'Scar Bay':
					cards += 2*len(getPlayers())
				
			for count in range(cards):
				c = pile.random()
				if c is None:
					whisper("No more {} cards to deal to location {}".format(details[0], location))
					break
				if getSiege() == True and c.Subtype in ('Monster','Barrier'): #This grabs monsters and barriers during siege scenarios and shunts them to the Scenario pile.
					whisper("In buildLocation, c.Type is {}, name is {}".format(c.Subtype,c.Name))
					c.moveTo(shared.piles['Special'])
				else:
					c.moveTo(locPile)
		else:
			whisper("Location error: Failed to parse [{}]".format(details[0]))
		location.link(locPile) # We do this at the end because doing it earlier causes major performance issues

# Check to see if all the locations have the Enemy Ship as the top card
# Return False if they are not, or True if they are
def checkFreeCaptains():
	won = True
	if lockPile(shared.piles['Internal']):
		locs = [ c for c in table if c.Type == 'Location' ]
		for c in locs:
			if len(c.pile()) == 0:
				won = False
			else:
				card = c.pile().top()
				card.moveTo(shared.piles['Internal'])
				if card.Name != 'Enemy Ship':
					won = False
				card.moveTo(c.pile())
		unlockPile(shared.piles['Internal'])
	return won
	
def advanceBlessingDeck():
	#Move the top card of the Blessing deck to the discard pile	
	pile = shared.piles['Blessing Deck']	
	scenario = findScenario(table)
	if scenario is None:
		return
	
	if len(pile) == 0:

		#If we are playing the adventure "Into the Eye" then there is no blessing deck so we have nothing to do
		if scenario.Name == "Into the Eye":
			return
		#If we are playing The Free Captains Regatta then we win if all the locations have the Enemy Ship as the top card
		if scenario.Name == "The Free Captains' Regatta":
			gameOver(checkFreeCaptains())
		else: # Out of time - the players have lost
			gameOver(False)	
		return

	notify("{} advances the Blessing Deck".format(me))
	pile.top().moveTo(shared.piles['Blessing Discard'])
	#In Treasure of Jemma Redclaw and Fall of Kenabres, villain is in the blessings deck... move it to the table
	if shared.piles['Blessing Discard'].top().Name in [ 'Jemma Redclaw','Brinebones','Khorramzadeh' ]:
		whisper("Moving villain to the table.")
		shared.piles['Blessing Discard'].top().moveToTable(PlayerX(len(getPlayers())+1),StoryY)
		if len(pile) > 0:
			pile.top().moveTo(shared.piles['Blessing Discard'])
		else:
			gameOver(False)
		
	#In The Land of the Blind, when you encounter a Gholdako in the blessings deck, move it to the top of a random open location
	if shared.piles['Blessing Discard'].top().Name in ('Gholdako'):
		whisper("Moving Gholdako to a random open location.")
		locs = [ c for c in table if isOpen(c) ]
		loc = locs[int(random()*len(locs))-1]
		shared.piles['Blessing Discard'].top().moveTo(loc.pile())
		whisper("Moved Gholdako to {}".format(loc.Name))
	
	# Here comes the flood has special end conditions
	flood = findCardByName(table, 'Here Comes the Flood')
	if flood is not None:
		# Check to see if all locations are empty
		cardsToExplore = 0
		for i in range(8): # Loop through 8 location decks
			cardsToExplore += len(shared.piles["Location{}".format(i+1)])
		if cardsToExplore > 0 and len(pile) > 0:
			flood = None
	if flood is not None: # Compare dead allies to rescued allies
		died = 0
		for c in shared.piles['Special']:
			returnToBox(c)
			if c.Subtype == 'Ally':
				died += 1
		saved = len(shared.piles['Scenario'])
		notify("You saved {} allies and lost {} allies".format(saved, died))
		gameOver(saved >= died)
			
def gameOver(won):
	if won:
		#Check to see if scenario rewards the players with loot
		scenario = findScenario(table)
		if scenario is not None and 'Loot: ' in scenario.Attr4:
			if scenario.Name == 'Assault on the Pinnacle': # Default parsing fails because loot has a comma in it!
				lootlist = ['Chellan, Sword of Greed']
			elif scenario.Name in ['The Fall of Kenabres', 'Under the Broken City', 'Lair of the Vile and Vicious', 'Tracking Down Templars']: #These scenarios have special loot options
				lootlist = ['Scale of Cloudwalking','Scale of Disguise','Scale of Resistance','Scale of Sacred Weaponry']
				if scenario.Name == 'Lair of the Vile and Vicious':
					lootlist.append('Radiance')
				notify("ATTENTION: Be sure to choose ONE Loot Scale from those placed on the board; banish the rest.")
			else:
				opt,items = scenario.Attr4.split('Loot: ',1)
				lootlist = items.split(', ')
				if scenario.Name == 'Island of the Damned':
					shipwreck = findCardByName(table, 'Shipwreck')
					if shipwreck is not None:
						lootlist.append('Alise Grogblud')
			for item in lootlist:
				lootCard = findCardByName(shared.piles['Loot'],item)
				if lootCard is None:
					whisper("Failed to find loot {}".format(item))
				else:
					lootCard.moveTo(shared.piles['Scenario'])
					debug("Adding scenario loot {}".format(item))
		loot = [ c for c in shared.piles['Scenario'] ]
		plunder = [ c for c in shared.piles['Plunder'] ]
		loot.extend(plunder)
		
	cleanupGame()				
	for p in getPlayers():
		if p == me:
			displayHand(me)
		else:
			remoteCall(p, "displayHand", [me])
			
	if won:
		x = -300
		for c in loot:
			c.moveToTable(x, 0)
			x += 32
			
		path = findPath(table)
		if path is not None:
			if path.Name == "Mummy's Mask":
				choices = [t.Name for t in shared.piles['Support'] if t.Subtype == 'Trader']
				choices.append("Already chosen")
				if len(choices) > 0:
					x = -300
					y = 100
					for player in getPlayers():
						choice = askChoice("Please choose a trader for {}:".format(player.name),choices)
						trader = findCardByName(shared.piles['Support'],choices[choice-1])
						if trader is not None:
							trader.moveToTable(x,y)
							x = x + 50
						else:
							whisper("Did not find chosen trader.")
					
				
		notify("You won the scenario")
	else:
		notify("You lost the scenario")
		
#Move all my cards back into my hand ordered by type
def displayHand(who):
	mute()
	debug("Display hand")
	for pile in [ me.hand, me.Buried, me.deck ]:
		for c in pile:
			if c.Type == 'Feat':
				c.moveTo(me.Buried)
			elif c.Subtype == 'Cohort' and c.Name != getCohort():
				returnToBox(c)
				whisper("Returning cohort {} to the box.".format(c.Name))
			else:
				c.moveTo(me.Discarded)
				
	#Now order the cards - in turn move cards of the given type to the hand
	for type in ["Token","Weapon","Spell","Item","Armor","Ally","Blessing"]:
		for c in me.Discarded:
			if c.Subtype == type or (c.Subtype == 'Loot' and c.Subtype2 == type):
				c.moveTo(me.hand)
	whisper("Expected card distribution is {}".format(getCards()))