#NoEnv
#SingleInstance Force
SendMode Input

; Automatically toggle DND when script runs
TrayTip, DND Toggle, Toggling DND mode..., 2, 1

; Wait a moment for the tooltip to show
Sleep, 500

; Send Windows + N to open notifications
Send, {LWin down}n{LWin up}

; Wait longer for the panel to fully open
Sleep, 1000

; Make sure the notifications panel has focus
WinActivate, ahk_class Windows.UI.Core.CoreWindow

; Wait a bit more
Sleep, 300

; Try multiple approaches to press Enter
Send, {Enter}
Sleep, 200

; If first Enter didn't work, try again
Send, {Enter}
Sleep, 200

; Alternative: Try Space key (sometimes works better)
Send, {Space}

; Show completion message
Sleep, 500
TrayTip, DND Toggle, DND toggle attempted!, 2, 1

; Close the notifications panel
Send, {Escape}

; Wait 2 seconds then exit the script
Sleep, 2000
ExitApp