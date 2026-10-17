#SingleInstance, Force
#Persistent
#NoEnv
#Warn
;#NoTrayIcon
Gui 1:-Caption +Border
Gui, 1:Margin, 0, 0
Gui 2:-Caption +Border
Gui, 2:Margin, 0, 0
Gui 3:-Caption +Border
Gui, 3:Margin, 0, 0
Gui 4:-Caption +Border
Gui, 4:Margin, 0, 0

set1=1
set2=1
set3=1
set4=1
set5=1

;set1
GUIRTITLE1=GUIRIGHTPICTITLE.png
GUIRTITLE2=GUIRIGHTPICTITLEBACK.png
;set2
GUITAG1=GUIRIGHTPICTAG.png
GUITAG2=GUIRIGHTPICTAGBACK.png
;set3
GUIACTIONS1=GUIRIGHTPICACTIONS.png
GUIACTIONS2=GUIRIGHTPICACTIONSBACK.png
;set4
GUIMISC1=GUIRIGHTPICMISC.png
GUIMISC2=GUIRIGHTPICMISCBACK.png
;set5
GUILTITLE1=GUILEFTPICTITLE.png
GUILTITLE2=GUILEFTPICTITLEBACK.png
;icons for left
GETONTAGPIC=GETONTAG.png
TAGMOVINGPIC=TAGMOVING.png
BUILDONTAGPIC=BUILDONTAG.png
MOUNTPIC=MOUNTTOTAG.png
STACKONTAGPIC=STACKONTAG.png
STACKONTAGTIGHTERPIC=STACKTIGHTER.png
DRAINSUPPPIC=DRAINSUPP.png
BURNLORDPIC=BURNLORD.png
TAKESUPPPIC=TAKESUPP.png
ENEMYINCPIC=ENEMYINC.png
DESTROYSIEGEPIC=DESTROYSIEGE.png
PVDPIC=PVDGATE.png
REFRESHBANNERPIC=REFBANNER.png
REFRESHBANDFPIC=REFFOODANDBANNER.png
BREAKPIC=BREAK.png
NOSUPPPIC=NOSUPPKEEP.png
GOPASTPIC=NOATTACK.png
TAKEWPPIC=TAKEWP.png

; ADD BUTTONS HERE
Gui, 1:Add, Picture,hwndPicture1 vPicture1 x3 y3 w144 h72, %GUIRTITLE2%
Gui, 1:Add, Picture,hwndPicture2 vPicture2 x3 y78 w144 h118, %GUITAG2%
Gui, 1:Add, Picture,hwndPicture3 vPicture3 x3 y199 w144 h118, %GUIACTIONS2%
Gui, 1:Add, Picture,hwndPicture4 vPicture4 x3 y320 w144 h118, %GUIMISC2%

Gui, 2:Add, Picture,hwndPicture5 vPicture5 x3 y3 w144 h72, %GUILTITLE2%

Gui, 2:Add, Picture,gGetOnTag x3 y78 w144 h59, %GETONTAGPIC%
Gui, 2:Add, Picture,gTagMoving x3 y137 w144 h59, %TAGMOVINGPIC%
Gui, 2:Add, Picture,gBuildOnTag x3 y199 w144 h59, %BUILDONTAGPIC%
Gui, 2:Add, Picture,gMountToCatch x3 y258 w144 h59, %MOUNTPIC%
Gui, 2:Add, Picture,gStackTag x3 y320 w144 h59, %STACKONTAGPIC%
Gui, 2:Add, Picture,gStackTighter x3 y379 w144 h59, %STACKONTAGTIGHTERPIC%

Gui, 3:Add, Picture,hwndPicture5 vPicture5 x3 y3 w144 h72, %GUILTITLE2%

Gui, 3:Add, Picture,gDrainSupp x3 y78 w144 h59, %DRAINSUPPPIC%
Gui, 3:Add, Picture,gBurnLord x3 y137 w144 h59, %BURNLORDPIC%
Gui, 3:Add, Picture,gTakeSupp x3 y199 w144 h59, %TAKESUPPPIC%
Gui, 3:Add, Picture,gEnemyInc x3 y258 w144 h59, %ENEMYINCPIC%
Gui, 3:Add, Picture,gDesSiege x3 y320 w144 h59, %DESTROYSIEGEPIC%
Gui, 3:Add, Picture,gPVD x3 y379 w144 h59, %PVDPIC%

Gui, 4:Add, Picture,hwndPicture5 vPicture5 x3 y3 w144 h72, %GUILTITLE2%

Gui, 4:Add, Picture,gRefBanner x3 y78 w144 h59, %REFRESHBANNERPIC%
Gui, 4:Add, Picture,gRefBandF x3 y137 w144 h59, %REFRESHBANDFPIC%
Gui, 4:Add, Picture,gBreak x3 y199 w144 h59, %BREAKPIC%
Gui, 4:Add, Picture,gDontSupp x3 y258 w144 h59, %NOSUPPPIC%
Gui, 4:Add, Picture,gWalkPast x3 y320 w144 h59, %GOPASTPIC%
Gui, 4:Add, Picture,gWP x3 y379 w144 h59, %TAKEWPPIC%

; GUI1 - BACKGROUND PICTURE is being added after the other GUI components 
Gui, 1:Add, Picture, x0 y0 w150 h450 +0x4000000, GUIRIGHTPIC.png
Gui, 1:Show,x1770 y350 w150 h450, ASCENDUPWARD
Gui, 1:+LastFound
Gui, 1:+AlwaysOnTop
Gui, 1:+ToolWindow
Gui, 2:Add, Picture, x0 y0 w150 h450 +0x4000000, GUILEFTPIC.png
Gui, 2:+LastFound
Gui, 2:+AlwaysOnTop
Gui, 2:+ToolWindow
Gui, 2:+Owner1
Gui, 3:Add, Picture, x0 y0 w150 h450 +0x4000000, GUILEFTPIC.png
Gui, 3:+LastFound
Gui, 3:+AlwaysOnTop
Gui, 3:+ToolWindow
Gui, 3:+Owner1
Gui, 4:Add, Picture, x0 y0 w150 h450 +0x4000000, GUILEFTPIC.png
Gui, 4:+LastFound
Gui, 4:+AlwaysOnTop
Gui, 4:+ToolWindow
Gui, 4:+Owner1



SetKeyDelay, 10, 10
SetTimer,MouseOverPicture,1
Return

;Functions
GetOnTag:
	MouseClick, Left, -500, 200
	sleep, 50
	send, +{enter}
	send,  Get on Tag{!}
	send, {enter}
	return

TagMoving:
	MouseClick, Left, -500, 200
	sleep, 50
	send, +{enter}
	send,  Tag is Moving{!}
	send, {enter}
	return

BuildOnTag:
	MouseClick, Left, -500, 200
	sleep, 50
	send, +{enter}
	send,  Build on Tag{!}
	send, {enter}
	return

MountToCatch:
	MouseClick, Left, -500, 200
	sleep, 50
	send, +{enter}
	send,  Mount up to Catch up{!}
	send, {enter}
	return

StackTag:
	MouseClick, Left, -500, 200
	sleep, 50
	send, +{enter}
	send,  Stack on Tag{!}
	send, {enter}
	return

StackTighter:
	MouseClick, Left, -500, 200
	sleep, 50
	send, +{enter}
	send,  Stack tighter on Tag{!}
	send, {enter}
	return

DrainSupp:
	MouseClick, Left, -500, 200
	sleep, 50
	send, +{enter}
	send,  Drain Supply{!}
	send, {enter}
	return

BurnLord:
	MouseClick, Left, -500, 200
	sleep, 50
	send, +{enter}
	send,  Burn Lord{!}
	send, {enter}
	return

TakeSupp:
	MouseClick, Left, -500, 200
	sleep, 50
	send, +{enter}
	send,  Take Supply{!}
	send, {enter}
	return

EnemyInc:
	MouseClick, Left, -500, 200
	sleep, 50
	send, +{enter}
	send,  Enemy Incoming{.} Get Ready{!}
	send, {enter}
	return

DesSiege:
	MouseClick, Left, -500, 200
	sleep, 50
	send, +{enter}
	send,  Destroy Siege{!}
	send, {enter}
	return

PVD:
	MouseClick, Left, -500, 200
	sleep, 50
	send, +{enter}
	send,  PVD the Gate{!}
	send, {enter}
	return

RefBanner:
	MouseClick, Left, -500, 200
	sleep, 50
	send, +{enter}
	send,  Refresh Banners{!}
	send, {enter}
	return

RefBandF:
	MouseClick, Left, -500, 200
	sleep, 50
	send, +{enter}
	send,  Refresh Banners and Food{!}
	send, {enter}
	return

Break:
	MouseClick, Left, -500, 200
	sleep, 50
	send, +{enter}
	send,  We are on break folks{!} Do whatever ya want{!}
	send, {enter}
	return

DontSupp:
	MouseClick, Left, -500, 200
	sleep, 50
	send, +{enter}
	send,  Don't take Supply from keep{!}
	send, {enter}
	return

WalkPast:
	MouseClick, Left, -500, 200
	sleep, 50
	send, +{enter}
	send,  Walk Past{!}
	send, {enter}
	return

WP:
	MouseClick, Left, -500, 200
	sleep, 50
	send, +{enter}
	send,  Take the Waypoint{!}
	send, {enter}
	return


MouseOverPicture:
Gui,Submit,NoHide
MouseGetPos,,,,id,2
if(id=Picture1)
{
	if(set1="1")
	{
		GuiControl,,Picture1,%GUIRTITLE1%
	set1=0
	}
	return
}
if(set1="0")
{
GuiControl,,Picture1,%GUIRTITLE2%
set1=1
}

if(id=Picture2)
{
	if(set2="1")
	{
		GuiControl,,Picture2,%GUITAG1%
		Gui, 2:Show,x1620 y350 w150 h450, ASCENDUPWARD
		sleep,1250
	set2=0
	}
	return
}
if(set2="0")
{
GuiControl,,Picture2,%GUITAG2%
Gui, 2:Hide
set2=1
}

if(id=Picture3)
{
	if(set3="1")
	{
		GuiControl,,Picture3,%GUIACTIONS1%
		Gui, 3:Show,x1620 y350 w150 h450, ASCENDUPWARD
		sleep,1250
	set3=0
	}
	return
}
if(set3="0")
{
GuiControl,,Picture3,%GUIACTIONS2%
Gui, 3:Hide
set3=1
}

if(id=Picture4)
{
	if(set4="1")
	{
		GuiControl,,Picture4,%GUIMISC1%
		Gui, 4:Show,x1620 y350 w150 h450, ASCENDUPWARD
		sleep,1250
	set4=0
	}
	return
}
if(set4="0")
{
GuiControl,,Picture4,%GUIMISC2%
Gui, 4:Hide
set4=1
}

if(id=Picture5)
{
	if(set5="1")
	{
		GuiControl,,Picture5,%GUILTITLE1%
	set5=0
	}
	return
}
if(set5="0")
{
GuiControl,,Picture5,%GUILTITLE2%
set5=1
}
return


