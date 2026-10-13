# Event feature index (all 164 tracked features)

Generated from `Tracking mapping Tile Match.xlsx`, sheet 'Triple Tile'. Each row below is one *Feature* tag in the source workbook, which usually groups several taxonomy rows (kingdom/phylum/class/order/family/genus/species = k/p/c/o/f/g/s) that together describe one game feature's events. `Flagged rows` counts rows where the analyst left a comment (e.g. `verified`, `checked`, `issue here`, `g field is incorrect`, `not coming`) — read `event_taxonomy_full.csv` for the exact comment before trusting a field on a flagged feature.

| Feature | Rows | Kingdom(s) (k) | Flagged rows | First description |
|---|---|---|---|---|
| install | 4 | device, device_info, install | 0 | To track installs (organic or paid) |
| DAU | 2 | dau, device_dau | 0 | When the user opens the application for the first time in the day |
| session | 3 | session | 0 | when a user resumes a session |
| Experiment | 1 | experiment | 0 | Experiment allocation |
| GDPR | 2 | dialog | 0 | When player interacts with gpdr popup |
| CCPA | 2 | dialog | 0 | When player interacts with data clean/request popups |
| Puzzle | 16 | puzzle, puzzle/ dp/ bonus_level, puzzle/dp/bonus_level | 5 | When player clears a puzzle |
| Puzzle  | 2 | puzzle | 2 | When a tile is moved from the board to the tile rack |
| LLP | 6 | sagamap | 0 | When the player views the home screen (saga map) |
| Settings | 12 | dialog | 6 | When the player views/closes the settings popup |
| Outro | 3 | dialog | 0 | When player views level outro on fail |
| Progression | 3 | dialog | 0 | When the player completes a chapter and views the chapter complete popup |
| Notif | 4 | local | 1 | When a notif is sent/clicked |
| w2e | 8 | ad_tracking, dialog | 2 | Whenever request is fired and w2e is loaded/ whenever w2e is not loaded on request |
| Android 13 Compliance | 3 | dialog, notif_permission | 0 | When user interacts with native notif permission popup  |
| Tutorial | 3 | dialog | 0 | When the tutorial is opened from the settings sreen |
| NACTA | 2 | puzzle | 0 | When the player sees a hint on a level |
| Rate Us | 9 | debug, dialog | 0 | When the player view/close/sad/happy the pre-popup for rate us |
| DLC | 8 | content _download, content_download, dialog, sagamap | 0 | Additional content downloads |
| Streak System | 1 | puzzle | 0 | When the player gets a streak |
| How to Play | 2 | dialog, puzzle | 0 | When the player taps on the how to play icon in the puzzle screen |
| Outro Debug | 2 | debug | 0 | When the player sees the next button o the level outro |
| Daily Challenge | 33 | daily_challenge, dialog, dp, local, sagamap | 2 | When the player views the DC unlock popup |
| Zen Tree | 2 | outro, puzzle | 0 | When the player gets the Zen Points in the level |
| Quit flow | 2 | dialog | 0 | When the player views the quit popup |
| Onboarding opts | 1 | dialog | 0 | When the player sees the 1st/2nd/3rd step o the tutorial |
| Poweerup locked feedback | 2 | dialog | 0 | When the player taps on the locked powerrup and sees the toaster |
| DLR | 3 | dialog, local | 0 | When the player views the DLR popup |
| Force Update | 2 | dialog | 0 | When the player view/closes/taps non update on the  soft force update popup |
| Build 32 | 5 | puzzle | 0 | Number of matches available in the first layer when the player views a level |
| FB connect | 4 | dialog | 3 | When the player views/interacts with the fb popup |
| Collect and Contunie on chapter complete | 1 | dialog | 0 | When the player collects the chapter complete reward |
| Home Screen experiment | 2 | sagamap | 0 | When the player taps on the hamster |
| DC optimizations | 4 | dialog, dp | 0 | When the player views the daily challenge popup on the outro |
| Notif Opts v1 | 2 | local | 0 | When the players gets/clicks on any of the D0/D1 notifs |
| IAP popup | 13 | dialog, puzzle, store | 0 | When the player views the IAP popup on tapping the powerup icon |
| How to Play opts | 2 | dialog | 0 | when the player taps on the settings screen |
| Hint System Opts | 2 | puzzle | 0 | When the player views on the 3 tile hint |
| Daily Challenge DLC | 2 | daily_challenge | 0 | When the player views the daily challenge screen and content is being downloaded |
| Hidden Tile Obstacle | 2 | puzzle | 0 | When the hidden tile is revealed |
| Viewers investigation | 2 | dialog, puzzle | 0 | when the player taps on the screen when the tutorial is active |
| perf | 7 | perf | 0 |  |
| Choose My Difficulty | 1 | dialog | 0 | When player interacts with choose difficulty popup |
| Chapter Complete Flow | 1 | dialog | 0 | When player views next chapter popup after collecting reward on chapter complete popup |
| Dynamic Difficulty v1 | 4 | puzzle, puzzle/dp/bonus_level | 1 | When the level eases due to dynamic difficulty |
| Golden Tile | 30 | cash, dialog, golden_tile, home, inventory, store | 27 | When golden tile event is assigned |
| Bonus Levels | 19 | bonus_level, dialog, puzzle | 0 | When player views a bonus level |
| Leaderboard Debug | 2 | content_download, content_load | 1 | When leaderboard config is loaded |
| DDA v2 | 2 | puzzle | 0 | When the leves eases due to guardrail |
| Econ | 18 | bonus_level, cash, dialog, dp, puzzle, sagamap, store | 9 | When the play taps on coin counter on puzzle screen |
| Online vs Offline | 4 | network | 4 | When app is launched ( start/ resume ) |
| w2e surfacing | 1 | dialog | 0 | When player clicks on w2e on store page |
| Sky Sprint | 18 | dialog, sagamap, sky_sprint | 4 | When sky sprint event is assigned |
| Streak Event | 14 | dialog, sagamap, streak_event | 1 | When lily's adv event is assigned |
| OOC Flow | 14 | dialog, puzzle/ dp/ bonus_level, store | 0 | When the player clicks on bundle/starter pack on the IAP popup  |
| w2e Cap | 5 | dialog, sagamap | 0 | When player clicks on w2e on outro |
| ad logic | 4 | ads_logic | 0 | When it ads is to be shown to the player |
| tile zoom | 1 | puzzle/ dp/ bonus_level | 0 | zoom factor of tile for each level |
| tracker based intersititial | 1 | tracker | 0 | when the tracker info of a player is checked |
| extra slot | 9 | bonus_level, dp, inventory, puzzle, puzzle/ dp/ bonus_level | 0 | When the player taps on the extra slot icon |
| fb login | 4 | login_page, user | 0 | when user views/ exits login page |
| ad mediation initialization | 1 | tracker_ads | 0 | when the tracker info of a player is checked for initializing ad sdks |
| w2e popup | 3 | dialog | 0 | when extra slot w2e popup is shown |
| w2e puzzle | 2 | dialog, puzzle/ dp/ bonus_level | 0 | when player clicks on w2e icon on gameboard |
| Localization | 6 | dialog, session | 5 | When the player taps on languages in the settings menu |
| EOC | 1 | dialog | 0 | on app launch this tracking is to be fired if player is ooc |
| Hard Level Tagging | 4 | dialog, puzzle | 2 | When players views a puzzle |
| Picnic Rush | 5 | dialog, picnic_rush, puzzle | 0 | When pu on board is allocated on level view |
| Free Hint Popup | 1 | dialog | 0 | When the player interacts with free hint popup |
| Play On | 2 | dialog | 0 | When player interacts with play on popup |
| DT auto update | 4 | dialog, local | 0 | when the player interacts dt auto update popup |
| w2e_store | 12 | cash, dialog, inventory | 11 | When the player taps on the free coins panel in the store |
| Leaderboard | 32 | content_download, content_load, dialog, home, leaderboard, p | 0 | When the player views the name change dialog |
| Stamps_event | 1 | dialog | 1 | When player sees an ftue for stamps event on puzzle screen |
| Lighting strike | 11 | bolts, cash, dialog, store | 0 | When bolts anim has started on puzzle screen |
| streak event  | 1 | debug | 0 | When the player taps anywhere on streak event intro popup |
| bonus level | 1 | debug | 0 | When the player taps anywhere on bonus level popup |
| play on  | 1 | debug | 0 | When the player taps anywhere on play on popup |
| dlr_debug | 23 | debug | 5 | When the player taps anywhere on dlr popup |
| dt_interstitial_exp | 2 | debug, preload_flag | 0 | After every one minute spent after install this tracking is to be sent ( for first 60 mins |
| Play On Opts | 1 | dialog | 0 | When player interacts with play on popup |
| win outro opts | 3 | dialog, puzzle | 0 | when player is entering the puzzle screen |
| it_tunings | 5 | debug | 1 | When player views first level of the session |
| w2e intro | 6 | debug, dialog, puzzle/dp/bonus_level, user_data, user_type | 0 | This tracking is to be fired whenever player goes to ooc from not ooc scenario |
| quest center | 18 | cash, dialog, home, quest_centre, user_data, user_type | 0 | player bucket details - to be fired once everyday for both control and variant  |
| RUX | 4 | cash, dialog, inventory, welcome_back | 0 | When player sees the welcome back pop up |
| GDPR v2 | 4 | dialog, user | 0 | When player views the GDPR on login screen pop up |
| no_matches available | 3 | dialog, puzzle/ dp, puzzle/dp | 0 | when the player view the the no match avaialble popup |
| Install  | 1 | device_info | 0 | When app is installed and launched for the first time |
| w2e_intro_debug | 2 | debug | 0 | To capture the exact time stamp of install |
| Powerup prompts | 5 | puzzle/ dp/ bonus_level, user_type | 2 | When pu prompt starts |
| Welcome Gift | 1 | dialog | 0 | when welcome gift popup is shown |
| Level Intro | 3 | dialog | 3 | when currency grant animation is started |
| loading_screen_debug | 1 | debug | 0 | When IT ad is requested from game side but ad is not shown by admon |
| rack feedback | 2 | puzzle/dp/bonus_level | 0 | when rack pulsate animation starts |
| CTA tap area increase | 1 | dialog | 0 | When the player taps on overlay which leads to popup close |
| Transition screen | 1 | dialog | 1 | when players sees loading screen before it ads |
| Wallet tracking | 1 | inventory | 0 | Player's coin counter value at the start of every session for each powerup |
| Lite SDK W2EQuest | 3 | cash, dialog | 0 | When W2E Quest dialog is surfaced on puzzle screen |
| Lite SDK Backup Xpromo | 2 | cash, dialog | 0 | When coin reward is granted for backup_xpromo |
| w2e_bonus_level | 4 | cash, dialog | 1 | When the player interacts with the w2_bonus_level |
| player bucketing | 1 | player_bucket | 1 | fired when the player plays the fiurst session in the day |
| picninc rush opts | 1 | debug | 1 | when a tile is not playable after using wand and the parent is removed |
| android notif 14 permsission improvements | 1 | dialog | 0 | when the nav bar is enables for android 14 |
| instagram follow button | 1 | dialog | 1 | When player clicks on instagram follow button  |
| notif pre prompt | 2 | dialog, puzzle | 0 | when user interacts with notif pre prompt pop up |
| Difficulty personalization | 1 | player_bucket | 0 | When the players get allocated to a player bucket |
| tile not iteractable issue | 1 | debug | 0 | When the player taps on a tile and its doesn't get added to the rack |
| notifs | 1 | local | 0 | when a notif is scheduled |
| loading bar | 1 | loading_bar | 0 | when players sees progress in loading bar |
| bubble pop | 12 | bubble, cash, dialog, puzzle | 9 | when the bubble is viewed |
|  DLR_w2e | 4 | cash, dialog | 2 | When the player interacts with DLR popup |
| DLR_w2e | 2 | dialog, inventory | 2 | When the player watches a video for second reward from the DLR popup |
| Lily's adventure | 3 | debug | 0 | debug for end state popup viewed |
| dc sticker load | 1 | daily_challenge | 0 | Status of all stickers(loaded/not loaded) when the player opens the sticker dialog |
| device details | 1 | device_details | 1 | When the user opens the application  |
| tile_rack_ftue | 6 | dialog | 6 | When the tutorial for tile rack is trigerred for the player  |
| iOS notifs | 1 | dialog | 0 | When player interacts with native notif permission pop up |
| ATT | 4 | dialog, ios14_idfa | 0 | when the player interacts with IDFA pre prompt |
| apple login | 2 | dialog, user | 0 | when player is able/ fails to login |
| Home Screen | 12 | dialog, home | 1 | When the player views the home screen |
| Mid level Gratification | 2 | puuzle/dp/bonus_level, puzle/dp/bonus_level | 2 | when a gratification is triggered |
| Symbol Unlock | 5 | dialog, symbol_unlock | 5 | When progress bar is viewed on win/ fail outro |
| Symbol unlock | 1 | home | 1 | When user views unlocked tile on home screen |
| Event Unlock | 6 | dialog, home | 6 | When player taps on locked leaderboard event icon on home screen |
| Faux H2P | 1 | dialog | 1 | When user gets a dialog for h2p on lev 2 |
| Golden tile | 1 | dialog | 1 | When Player interacts with golden tile pop up under locked state |
| No Ads Pack | 11 | cash , debug, dialog, home/sagamap, store | 5 | When the player taps on the no ads pack on the home screen/sagamap |
| Stamps | 15 | dialog, home, stamps_event | 0 | When player interacts with locked icon of stamps event on home screen |
| Profile | 6 | dialog, home | 1 | When player interacts with profile icon on home screen |
| Wisdom score | 2 | home, wisdom_score | 0 | when the player gets the wisdom score at the end of the level |
| content experiment | 1 | content_version | 0 | when the player gets a content version assigned at the start of the level |
| home screen debug | 1 | debug | 0 | when player comes on home screen and it is not loaded |
| Golden Tile Play On | 1 | dialog | 1 | When player interacts with play on popup |
| no_ads failure | 1 | debug | 0 | when no_ads _pack grant does not happen |
|  DLR | 1 | cash | 1 | When the player gets the reward for the 7th day on the DLR popup |
| Notify me | 3 | dialog, home | 2 | When the player views the notify me popup |
| Notify_me | 1 | local | 0 | When the permission for sending notifs is changed |
| New Conversion Deals | 5 | cash , dialog, home, store | 5 | When the player views the popup for IAP deals |
| Powerup IAP | 2 | cash | 0 | When player gets a powerup using w2e |
| fb coins | 1 | cash | 0 | When coins are granted to the player for logging in |
| Hint on tile rack | 3 | puzzle/ dp/ bonus_level | 3 | When the player taps on the tile rack |
| Store ui | 1 | dialog | 1 | When player clicks on more offers cta on store page |
| DLR Revamp | 6 | dialog | 0 | When the player views the DLR popup |
| updated settings tracking | 2 | dialog | 0 | when the player interacts with settings popup |
| Social proofing | 4 | debug, dialog | 2 | When player interacts with social proofing level intro popup |
| Powerup prompts v2 | 5 | cash, dialog | 5 | When pu prompt starts |
| Play on with w2e | 3 | debug, dialog | 3 | When player interacts with play on popup |
| outro timing change | 1 | dialog | 1 | When player sees the level outro gratification |
| quest center opts v1 | 4 | dialog, puzzle/bonus_level/dp | 1 | when the player taps the quest icon on the puzzle screen |
| matches available | 7 | puzzle | 0 | When matches available is checked  |
| w2e_outro | 6 | cash, dialog, inventory, w2e_outro | 1 | When player interacts with w2e CTA on the outro |
| First Try Win | 1 | dialog | 0 | When Player interacts with first try win gratification dialog after puzzle clear |
| Level CTA on Outro | 6 | bonus_level, dialog, puzzle  | 5 | When player interacts with Level CTA / home button on the outro |
| symbols live ops | 1 | symbols_ui | 0 | When player gets symbols assigned for the day |
| Daily Victory | 6 | cash, dialog, home, login_streak | 0 | When the player interacts with the DLR popup |
| ads on inactivity | 4 | dialog | 0 | when ads on inactivity toaster is shown |
| audio ads | 6 | dialog | 0 | when audio ads toaster is shown |
| Updated DLC | 4 | content_download, dialog | 0 | updated tracking for dlc popup |
| wand debug | 1 | debug | 0 | tracking related to wand usage will be in following format |
| animation debug | 1 | debug | 0 | tracking related to animation will be in following format |
| wand debug error | 1 | debug | 0 | tracking related to wand when error is triggered will be in following format |
| QMT | 3 | puzzle, puzzle/dp/bonus_level | 1 | When qmt tiles are allocated on the board on level view |
| bots_lb | 3 | leaderboard | 2 | When score of player is changed in lb |
