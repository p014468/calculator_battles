import json
import os
import logging
import traceback
import re

from STATS_CALC_config import TOKEN, DIR, CHANNEL_ID, ADMIN_ID, SUPER_ADMIN_ID, OWNER_ID
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler
from emoji import emojize

updater = Updater(token=TOKEN, use_context = True)
dispatcher = updater.dispatcher

# load / update user, admin, owner lists
def loadUsers():
    with open(DIR + 'USER_ID.json', 'r') as fl:
        USER_ID = json.load(fl)
    return USER_ID

def loadAdmins():
    with open(DIR + 'ADMIN_ID.json', 'r') as fl:
        ADMIN_ID = json.load(fl)
    return ADMIN_ID

def loadOwners():
    with open(DIR + 'OWNER_ID.json', 'r') as fl:
        OWNER_ID = json.load(fl)
    return OWNER_ID

def updateUsers(USER_ID):
    with open(DIR + 'USER_ID.json', 'w') as fl:
        json.dump(USER_ID, fl, indent=2)
    return

def updateAdmins(ADMIN_ID):
    with open(DIR + 'ADMIN_ID.json', 'w') as fl:
        json.dump(ADMIN_ID, fl, indent=2)
    return

def updateOwners(OWNER_ID):
    with open(DIR + 'OWNER_ID.json', 'w') as fl:
        json.dump(OWNER_ID, fl, indent=2)
    return

# initialize user list, admin list and owner list
USER_ID = loadUsers()
ADMIN_ID = loadAdmins()
OWNER_ID = loadOwners()

# set up emojis used in battle stats report
morning_time = emojize(':full_moon_with_face:', use_aliases=True)
day_time = emojize(':sun_with_face:', use_aliases=True)
night_time = emojize(':new_moon_with_face:', use_aliases=True)

skala = emojize(':black_heart:', use_aliases=True)
oplot = '☘️'#emojize(':shamrock:', use_aliases=True)
night = emojize(':bat:', use_aliases=True)
roza = emojize(':rose:', use_aliases=True)
amber = emojize(':maple_leaf:', use_aliases=True)
ferma = emojize(':eggplant:', use_aliases=True)
tortuga = emojize(':turtle:', use_aliases=True)

# emojis to parse battle stats, battle report; to form keyboard, reports etc 
crossed_swords = emojize(':crossed_swords:', use_aliases=True)
shield = emojize(':shield:', use_aliases=True)
zp = emojize(':sunglasses:', use_aliases=True)
ga = emojize(':trident:', use_aliases=True)
lightning = emojize(':zap:', use_aliases=True)
easydef = emojize(':ok_hand:', use_aliases=True)
sleepingFace = emojize(':sleeping:', use_aliases=True)
fire = emojize(':fire:', use_aliases=True)
moneybag = emojize(':moneybag:', use_aliases=True)
res = emojize(':package:', use_aliases=True)
heart = emojize(':heart:', use_aliases=True)

# misc emojis
black_small_square = emojize(':black_small_square:', use_aliases=True)

# 0 1 2 3 4 5 - for consecutive steps in Conversation handler
BATTLE_STATS, CHOOSE_REPORT_TYPE, ATTACK_REPORT, DEFENCE_REPORT, CALC_ATTACK, CALC_DEFENCE = range(6)

# define global variables
bs = '' # name of parsed & normalised battle stats
breachedCastle = ''
protectedCastle = ''
day = ''
month = ''
year = ''
time = ''
breachedCastleInfo = {}
protectedCastleInfo = {}
report_link = ''

# service functions

def isUser(id):
    return id in USER_ID

def isAdmin(id):
    return id in ADMIN_ID

def isOwner(id):
    return id in OWNER_ID

def representsInt(s):
    try: 
        int(s)
        return True
    except ValueError:
        return False

# end service functions

# define function to handle unknown commande
def unknown(update, context):
    context.bot.send_message(update.effective_chat.id, '¯\\_(ツ)_/¯')

# define function to work with /start command
def start(update, context):
    chat_id = update.effective_chat.id
    if not isUser(chat_id):
        context.bot.send_message(chat_id, 'You are not user. Please contact @magnusmax for an access.')
        return ConversationHandler.END # stop conversation
    else:
        context.bot.send_message(chat_id, 'Hello. I can calculate damage or defence for a certain battle.\nPlease forward me battle stats from @ChatWarsDigestsBot or type /use_prev to use previously submitted battle stats. To stop type /cancel.')
    return BATTLE_STATS # next step to get battle stats

def formPrevBattleStats(d):
    text = 'Following battle stats will be used:\n'
    for i in range(len(d['breached'])): # walk through breached castles and gather info
        text = text + (d['breached'][i]['dayTime'] + '\n' if i == 0 else '') + d['breached'][i]['castle'] + ' <code>' + d['breached'][i]['points'] + '</code> ' + d['breached'][i]['breachType'] + ' ' + d['breached'][i]['gold'] + moneybag + '\n'
    for i in range(len(d['protected'])): # walk through protected castles and gather info
        text = text + d['protected'][i]['castle'] + ' <code>' + d['protected'][i]['points'] + '</code> ' + d['protected'][i]['breachType'] + ' ' + d['protected'][i]['gold'] + moneybag + '\n'
    return text

def getLastBattleStatsDateTime(DIR, suffix):
    filesList = []
    for subdir, dirs, files in os.walk(DIR): # go through each and avery instanse in the DIR directory, where files are stored as lists for each directory
        for f in files: # go through each file in files list
            if f.find(suffix) > 0: # if we find username or user_id in filename then add it to the list
                filesList.append(f)
    return max(filesList) # get the latest file

def getUserBattleStats(DIR, suffix):
    filesList = []
    for subdir, dirs, files in os.walk(DIR): # go through each and avery instanse in the DIR directory, where files are stored as lists for each directory
        for f in files: # go through each file in files list
            if f.find(suffix) > 0: # if we find username or user_id in filename then add it to the list
                filesList.append(f)
    return filesList # get the latest file    

# save battle stats from CWDigestBot
def saveBattleStats(update, context):
    global day
    global month
    global year
    global time
    global bs
    d = {} # define empty dict
    d['breached'] = [] # define key 'breached' and value as empy list to store information about breached castle
    d['protected'] = [] # define key 'protected' and value as empy list to store information about protected castle
    chat_id = update.effective_chat.id
    message = update.message.text
    username = update.effective_chat.username
    if username is None:
        suffix = chat_id
    else:
        suffix = username
    if message == '/cancel':
        cancel(update, context)
        return ConversationHandler.END
    elif message == '/use_prev' and len(bs) != 0: # if user wants to use previous report. len(bs) checks if variable is already stores info about previously submitted report
        try:
            with open(bs, 'r', encoding='utf-8') as json_file:
                d = json.load(json_file) # open .json file into dict d
            text = formPrevBattleStats(d)
            reply_keyboard = [[crossed_swords + 'Attack', shield + 'Defence']]
            context.bot.send_message(
                chat_id=chat_id, 
                text= text + '\n' + 'Please choose what stats you want to calculate?', 
                reply_markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=True),
                parse_mode='HTML')
            return CHOOSE_REPORT_TYPE
        except Exception:
            logging.error(traceback.format_exc())
    elif message == '/use_prev' and len(bs) == 0:  # if user wants to use previous report. len(bs) checks if variable is already stores info about previously submitted report
        text = 'Following battle stats will be used:\n'
        '''
        filesList = []
        for subdir, dirs, files in os.walk(DIR): # go through each and avery instanse in the DIR directory, where files are stored as lists for each directory
            for f in files: # go through each file in files list
                if f.find(suffix) > 0: # if we find username or user_id in filename then add it to the list
                    filesList.append(f)
        lastFile = max(filesList) # get the latest file
        '''
        lastFile = getLastBattleStatsDateTime(DIR, suffix)
        try:
            bs = DIR + lastFile # set the full path & file name of the battle stats
            with open(bs, 'r', encoding='utf-8') as json_file:
                d = json.load(json_file)
            text = formPrevBattleStats(d)
            reply_keyboard = [[crossed_swords + 'Attack', shield + 'Defence']]
            context.bot.send_message(
                chat_id=chat_id, 
                text= text + '\n' + 'Please choose what stats you want to calculate?', 
                reply_markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=True),
                parse_mode='HTML')
            return CHOOSE_REPORT_TYPE
        except Exception:
            logging.error(traceback.format_exc())

    elif update.message.forward_from == None or (update.message.forward_from != None and update.message.forward_from.id != 924278817):
        context.bot.send_message(chat_id, 'Please forward me battle stats from @ChatWarsDigestsBot. To cancel type /cancel')
        return BATTLE_STATS
    else:
        fullBattleStats = message.split('\n\n')
        day = fullBattleStats[0][2:4]
        month = fullBattleStats[0][5:7]
        year = '2021'
        if fullBattleStats[0][0] == morning_time:
            time = '09:00'
        elif fullBattleStats[0][0] == day_time:
            time = '17:00'
        elif fullBattleStats[0][0] == night_time:
            time = '01:00'
        else:
            time = '???'
        dayTime = day + '.' + month + '.' + year + ' ' + time
        bs = DIR + year + month + day + '_' + time[0:2] + '00_' + 'bs_' + suffix + '.json'
        report_link = fullBattleStats[5]
        context.bot.send_message(chat_id, report_link)

        if 'breached' in fullBattleStats[1]:
            breachedCastles = fullBattleStats[2].splitlines()
            try:
                for i in range(len(breachedCastles)):
                    if len(breachedCastles[i].split(' ')) == 3:
                        gold = '0'
                        castle, points, breachType = breachedCastles[i].split(' ')
                    else:
                        castle, points, breachType, gold = breachedCastles[i].split(' ')
                        gold = gold[:-1]
                    d['breached'].append({'castle':castle, 'dayTime':dayTime, 'breachType':breachType, 'points':points, 'gold':gold, 'damage':0})
            except Exception:
                logging.error(traceback.format_exc())
        elif 'breached' in fullBattleStats[3]:
            breachedCastles = fullBattleStats[4].splitlines()
            for i in range(len(breachedCastles)):
                if len(breachedCastles[i].split(' ')) == 3:
                    gold = '0'
                    castle, points, breachType = breachedCastles[i].split(' ')
                else:
                    castle, points, breachType, gold = breachedCastles[i].split(' ')
                    gold = gold[:-1]
                d['breached'].append({'castle':castle, 'dayTime':dayTime, 'breachType':breachType, 'points':points, 'gold':gold, 'damage':0})
        else:
            print('???')
        
        if 'protected' in fullBattleStats[1]:
            breachedCastles = fullBattleStats[2].splitlines()
            for i in range(len(breachedCastles)):
                if len(breachedCastles[i].split(' ')) == 3:
                    gold = '0'
                    castle, points, breachType = breachedCastles[i].split(' ')
                else:
                    castle, points, breachType, gold = breachedCastles[i].split(' ')
                    gold = gold[:-1]
                d['protected'].append({'castle':castle, 'dayTime':dayTime, 'breachType':breachType, 'points':points, 'gold':gold, 'protection':0})
        elif 'protected' in fullBattleStats[3]:
            breachedCastles = fullBattleStats[4].splitlines()
            for i in range(len(breachedCastles)):
                if len(breachedCastles[i].split(' ')) == 3:
                    gold = '0'
                    castle, points, breachType = breachedCastles[i].split(' ')
                else:
                    castle, points, breachType, gold = breachedCastles[i].split(' ')
                    gold = gold[:-1]
                d['protected'].append({'castle':castle, 'dayTime':dayTime, 'breachType':breachType, 'points':points, 'gold':gold, 'protection':0})
        else:
            print('???')

        if not os.path.isfile(bs):
            with open(bs, 'w', encoding='utf-8') as file:
                json.dump(d, file, indent=4, ensure_ascii=False)

        reply_keyboard = [[crossed_swords + 'Attack', shield + 'Defence']]
        context.bot.send_message(
            chat_id=chat_id, 
            text='Please choose what stats you want to calculate?', 
            reply_markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=True))
        return CHOOSE_REPORT_TYPE

def chooseReportType(update, context):
    chat_id = update.effective_chat.id
    message = update.message.text
    #reply_keyboard = [[tortuga, roza, amber], [ferma, oplot, night], [skala]]
    row1 = []
    row2 = []
    row3 = []
    if message == crossed_swords + 'Attack':
        with open(bs, 'r', encoding='utf-8') as json_file:
            d = json.load(json_file)
        #ls = []
        for i in range(len(d['breached'])):
            if i < 3:
                row1.append(d['breached'][i]['castle'])
            elif i < 6:
                row2.append(d['breached'][i]['castle'])
            else:
                row3.append(d['breached'][i]['castle'])
        reply_keyboard = [row1, row2, row3]
        context.bot.send_message(
            chat_id,
            'Please choose a castle:',
            reply_markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=True)
        )
        return ATTACK_REPORT
    elif message == shield + 'Defence':
        with open(bs, 'r', encoding='utf-8') as json_file:
            d = json.load(json_file)
        #ls = []
        for i in range(len(d['protected'])):
            if i < 3:
                row1.append(d['protected'][i]['castle'])
            elif i < 6:
                row2.append(d['protected'][i]['castle'])
            else:
                row3.append(d['protected'][i]['castle'])
        reply_keyboard = [row1, row2, row3]
        context.bot.send_message(
            chat_id,
            'Please choose a castle:',
            reply_markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=True)
        )
        return DEFENCE_REPORT
    else:
        #context.bot.send_message(chat_id, 'Wrong input. Try again /start.', reply_markup = ReplyKeyboardRemove())
        #return ConversationHandler.END
        context.bot.send_message(chat_id, 'Wrong input. Please choose what stats you want to calculate? To cancel type /cancel')
        return CHOOSE_REPORT_TYPE

def getAttackReport(update, context):
    global breachedCastle
    global breachedCastleInfo
    chat_id = update.effective_chat.id
    breachedCastle = update.message.text
    if not breachedCastle in tortuga+roza+amber+ferma+oplot+night+skala:
        #context.bot.send_message(chat_id, 'Worng input. Try again /start.', reply_markup = ReplyKeyboardRemove())
        #return ConversationHandler.END
        context.bot.send_message(chat_id, 'Worng input. Please choose a castle. To cancel type /cancel')
        return ATTACK_REPORT
    else:
        try:
            with open(bs, 'r', encoding='utf-8') as json_file:
                d = json.load(json_file)
                for i in range(len(d['breached'])):
                    if d['breached'][i]['castle'] == breachedCastle:
                        breachedCastleInfo[breachedCastle] = {'dayTime': d['breached'][i]['dayTime'], 'breachType': d['breached'][i]['breachType'], 'points': d['breached'][i]['points'], 'gold': d['breached'][i]['gold'], 'damage': d['breached'][i]['damage']}
                #print(breachedCastleInfo)
        except Exception:
            logging.error(traceback.format_exc())

    context.bot.send_message(update.effective_chat.id, 'Please send the attack report or just attack and gold from the report, e.g. 240 24.', reply_markup = ReplyKeyboardRemove())
    return CALC_ATTACK

def calcAttack(update, context):
    global breachedCastleInfo
    chat_id = update.effective_chat.id
    message = update.message.text
    try:
        if 'Твои результаты в бою' in message:
            attack = message[message.find(':')+1:message.find(' ', message.find(':')+1)]
            if attack.find('(') != -1:
                attack = attack[:attack.find('(')]
            #attack = message[message.find(crossed_swords+':')+2:message.find(' ', message.find(crossed_swords+':')+2)]
            #defence = message[message.find(shield+':')+2:message.find(' ', message.find(shield+':')+2)]
            #exp = message[message.find(':', message.find(fire))+2:message.find('\n', message.find(fire))]
            goldReport = message[message.find(':', message.find(moneybag))+2:message.find('\n', message.find(moneybag))]
            #stock = message[message.find(':', message.find(res))+2:message.find('\n', message.find(res))]
            #hp = message[message.find(':', message.find(heart))+2:]
            breachedCastleInfo[breachedCastle]['damage'] = int(-1 * (int(attack) / int(goldReport)) * int(breachedCastleInfo[breachedCastle]['gold']))
            with open(bs, 'r', encoding='utf-8') as json_file:
                d = json.load(json_file)
            for i in range(len(d['breached'])):
                if d['breached'][i]['castle'] == breachedCastle:
                    d['breached'][i]['damage'] = breachedCastleInfo[breachedCastle]['damage']
            with open(bs, 'w', encoding='utf-8') as file:
                json.dump(d, file, indent=4, ensure_ascii=False)
            context.bot.send_message(chat_id, 'Attack: ' + str(breachedCastleInfo[breachedCastle]['damage']) + '. Data is saved.\nTo form a report type /report YYYY MM DD HH')
            return ConversationHandler.END
        #elif message.find(' ') != -1 and len(message.split(' ')) == 2 and representsInt(message.split(' ')[0]) and representsInt(message.split(' ')[1]): 
        elif len(re.findall(r'(^\d+)(\s|/)(\d+$)', message)) == 1:
            #attack, goldReport = message.split(' ')
            attack = re.search(r'(^\d+)(\s|/)(\d+$)', message).group(1)
            goldReport = re.search(r'(^\d+)(\s|/)(\d+$)', message).group(3)
            breachedCastleInfo[breachedCastle]['damage'] = int(-1 * (int(attack) / int(goldReport)) * int(breachedCastleInfo[breachedCastle]['gold']))
            with open(bs, 'r', encoding='utf-8') as json_file:
                d = json.load(json_file)
            for i in range(len(d['breached'])):
                if d['breached'][i]['castle'] == breachedCastle:
                    d['breached'][i]['damage'] = breachedCastleInfo[breachedCastle]['damage']
            with open(bs, 'w', encoding='utf-8') as file:
                json.dump(d, file, indent=4, ensure_ascii=False)
            context.bot.send_message(chat_id, 'Attack: ' + str(breachedCastleInfo[breachedCastle]['damage']) + '. Data is saved.\nTo form a report type /report YYYY MM DD HH')
            return ConversationHandler.END
        else:
            context.bot.send_message(chat_id, 'Wrong input. Please send the attack report or just attack and gold from the report, e.g. 240 24. To cancel type /cancel')
            return CALC_ATTACK
    except Exception:
        logging.error(traceback.format_exc())

def getDefenceReport(update, context):
    global protectedCastle
    global protectedCastleInfo
    chat_id = update.effective_chat.id
    protectedCastle = update.message.text
    if not protectedCastle in tortuga+roza+amber+ferma+oplot+night+skala:
        context.bot.send_message(chat_id, 'Worng input. Please choose a castle. To cancel type /cancel')
        return DEFENCE_REPORT
    else:
        try:
            with open(bs, 'r', encoding='utf-8') as json_file:
                d = json.load(json_file)
                for i in range(len(d['protected'])):
                    if d['protected'][i]['castle'] == protectedCastle:
                        protectedCastleInfo[protectedCastle] = {'dayTime': d['protected'][i]['dayTime'], 'breachType': d['protected'][i]['breachType'], 'points': d['protected'][i]['points'], 'gold': d['protected'][i]['gold'], 'protection': d['protected'][i]['protection']}
                #print(protectedCastleInfo)
        except Exception:
            logging.error(traceback.format_exc())

    context.bot.send_message(update.effective_chat.id, 'Please send the defence report or just defence and gold from the report, e.g. 350 14.', reply_markup = ReplyKeyboardRemove())
    return CALC_DEFENCE

def calcDefence(update, context):
    global protectedCastleInfo
    chat_id = update.effective_chat.id
    message = update.message.text
    try:
        if 'Твои результаты в бою' in message:
            #attack = message[message.find(crossed_swords+':')+2:message.find(' ', message.find(crossed_swords+':')+2)]
            defence = message[message.find(shield+':')+2:message.find(' ', message.find(shield+':')+2)]
            if defence.find('(') != -1:
                defence = defence[:defence.find('(')]
            #exp = message[message.find(':', message.find(fire))+2:message.find('\n', message.find(fire))]
            goldReport = message[message.find(':', message.find(moneybag))+2:message.find('\n', message.find(moneybag))]
            #stock = message[message.find(':', message.find(res))+2:message.find('\n', message.find(res))]
            #hp = message[message.find(':', message.find(heart))+2:]
            protectedCastleInfo[protectedCastle]['protection'] = int(int(protectedCastleInfo[protectedCastle]['gold']) / (int(goldReport) / int(defence)))
            with open(bs, 'r', encoding='utf-8') as json_file:
                d = json.load(json_file)
            for i in range(len(d['protected'])):
                if d['protected'][i]['castle'] == protectedCastle:
                    d['protected'][i]['protection'] = protectedCastleInfo[protectedCastle]['protection']
            with open(bs, 'w', encoding='utf-8') as file:
                json.dump(d, file, indent=4, ensure_ascii=False)
            context.bot.send_message(chat_id, 'Defence: ' + str(protectedCastleInfo[protectedCastle]['protection']) + '. Data is saved.\nTo form a report type /report YYYY MM DD HH')
            return ConversationHandler.END
        #elif message.find(' ') != -1 and len(message.split(' ')) == 2 and representsInt(message.split(' ')[0]) and representsInt(message.split(' ')[1]):
        elif len(re.findall(r'(^\d+)(\s|/)(\d+$)', message)) == 1:
            #defence, goldReport = message.split(' ')
            defence = re.search(r'(^\d+)(\s|/)(\d+$)', message).group(1)
            goldReport = re.search(r'(^\d+)(\s|/)(\d+$)', message).group(3)
            protectedCastleInfo[protectedCastle]['protection'] = int(int(protectedCastleInfo[protectedCastle]['gold']) / (int(goldReport) / int(defence)))
            with open(bs, 'r', encoding='utf-8') as json_file:
                d = json.load(json_file)
            for i in range(len(d['protected'])):
                if d['protected'][i]['castle'] == protectedCastle:
                    d['protected'][i]['protection'] = protectedCastleInfo[protectedCastle]['protection']
            with open(bs, 'w', encoding='utf-8') as file:
                json.dump(d, file, indent=4, ensure_ascii=False)
            context.bot.send_message(chat_id, 'Defence: ' + str(protectedCastleInfo[protectedCastle]['protection']) + '. Data is saved.\nTo form a report type /report YYYY MM DD HH')
            return ConversationHandler.END
        else:
            context.bot.send_message(chat_id, 'Wrong input. Please send the defence report or just defence and gold from the report, e.g. 350 14. To cancel type /cancel')
            return CALC_DEFENCE
    except Exception:
        logging.error(traceback.format_exc())

def cancel(update, context):
    chat_id = update.effective_chat.id
    context.bot.send_message(chat_id, 'To restart, press /start.', reply_markup = ReplyKeyboardRemove())
    return ConversationHandler.END

def report(update, context):
    chat_id = update.effective_chat.id
    message = update.message.text
    username = update.effective_chat.username
    if username is None:
        suffix = chat_id
    else:
        suffix = username
    if not isUser(chat_id):
        context.bot.send_message(chat_id, 'You are not user. Please contact @magnusmax for an access.')
        return
    else:
        if message == '/report':
            lastFile = getLastBattleStatsDateTime(DIR, suffix)
            bs = DIR + lastFile # set the full path & file name of the battle stats
            #context.bot.send_message(chat_id, 'first condition')
            year = lastFile[:4]
            month = lastFile[4:6]
            day = lastFile[6:8]
            time = lastFile[9:11]
        elif message.find(' ') == -1:
            context.bot.send_message(chat_id, 'Invalid format. Type /report YYYY MM DD HH')
            return
        else:
            command, year, month, day, time = message.split(' ')
            bs = DIR + year + month + day + '_' + time + '00_' + 'bs_' + suffix + '.json' 
        try:
            with open(bs, 'r', encoding='utf-8') as json_file:
                d = json.load(json_file)
            text = day + '.' + month + '.' + year + ' ' + time +':00' + '\n'
            ln = len(text)
            total_atk = 0
            total_def = 0
            for i in range(len(d['protected'])):
                if d['protected'][i]['breachType'] != easydef and d['protected'][i]['breachType'] != sleepingFace:
                    text = text + d['protected'][i]['castle'] + ':' + d['protected'][i]['breachType'] + (shield if d['protected'][i]['breachType'] == ga or d['protected'][i]['breachType'] == lightning else '') + str(round(d['protected'][i]['protection']/1000,1)) + 'k\n'
                    total_def = total_def + round(d['protected'][i]['protection']/1000,1)
            for i in range(len(d['breached'])):
                text = text + d['breached'][i]['castle'] + ':' + d['breached'][i]['breachType'] + str(round(d['breached'][i]['damage']/1000,1)) + 'k\n'
                total_atk = total_atk + round(d['breached'][i]['damage']/1000,1)
            text = text + '-'*ln + '\n' + ('Total' + shield + ': ' + str(round(total_def,1)) + 'k\n' if total_def != 0 else '') + 'Total' + crossed_swords + ': ' + str(round(total_atk,1)) + 'k'
            #print(text)
            context.bot.send_message(chat_id, text)
        except Exception:
            logging.error(traceback.format_exc())

def listBattleStats(update, context):
    chat_id = update.effective_chat.id
    message = update.message.text
    username = update.effective_chat.username
    if username is None:
        suffix = chat_id
    else:
        suffix = username
    if not isOwner(chat_id):
        context.bot.send_message(chat_id, 'You are not owner. Please contact @magnusmax for an access.')
        return
    else:
        try:
            if message == '/list':
                listFiles = getUserBattleStats(DIR, suffix)
            elif message == '/list all':
                dc = {}
                ls = getUserBattleStats(DIR, '_bs_')
                for i in range(len(ls)):
                    if ls[i][ls[i].find('bs_')+3:ls[i].find('.json')] not in dc: # check if user is in dict
                        dc[ls[i][ls[i].find('bs_')+3:ls[i].find('.json')]] = 1
                    else:
                        dc[ls[i][ls[i].find('bs_')+3:ls[i].find('.json')]] += 1
                text = 'List of users and number of submitted battle stats:\n'
                for key in dc:
                    text = text + black_small_square + key + ': <code>' + str(dc[key]) + '</code>\n'
                context.bot.send_message(chat_id, text, parse_mode = 'HTML')
                return
            else:
                command, suffix = message.split(' ')
                listFiles = getUserBattleStats(DIR, suffix)
            listFiles.sort()
            nrBattleStats = len(listFiles)
            text = 'The user <b>' + suffix + '</b> has <b>' + str(nrBattleStats) + '</b> reports. The last ' + str(min(3, len(listFiles))) + ' are:\n'
            for i in range(min(3, len(listFiles))):
                text = text + black_small_square + '<code>' + listFiles[-1-i][:4]+' '+listFiles[-1-i][4:6]+' '+listFiles[-1-i][6:8]+' '+listFiles[-1-i][9:11]+':00'+ '</code>\n'
            context.bot.send_message(chat_id, text, parse_mode='HTML')
        except Exception:
            logging.error(traceback.format_exc())


def msg(update, context):
    context.bot.send_message(update.effective_chat.id, '¯\\_(ツ)_/¯')
    '''
    if not update.message.reply_to_message is None:
        replied_info = update.message.reply_to_message
        context.bot.send_message(chat_id, str(replied_info))
    '''

def send(update, context):
    chat_id = update.effective_chat.id
    if not isAdmin(chat_id):
        context.bot.send_message(chat_id, 'You are not admin. Please contact @magnusmax for an access.')
    elif update.message.reply_to_message is None:
        context.bot.send_message(chat_id, 'You have to reply on the message to send it to the channel.')
    else:
        replied_info = update.message.reply_to_message
        try:
            if 'Total' in replied_info.text: # ' + crossed_swords + ': '
                context.bot.forward_message(CHANNEL_ID, chat_id, replied_info.message_id)
            else:
                context.bot.send_message(chat_id, 'It\'s not a summary.')
        except Exception:
            logging.error(traceback.format_exc())

def addAdmin(update, context):
    chat_id = update.effective_chat.id
    message = update.message.text
    if not isOwner(chat_id):
        context.bot.send_message(chat_id, 'You are not owner. Please contact @magnusmax for an access.')
        return
    else:
        try:
            if len(re.findall(r'/add_admin\s\d+\s[0-2]', message)) != 1:
                context.bot.send_message(chat_id, 'Bad format. Type command, id and user type separated by space, e.g. /add_admin 123 1. User types are:\n0 - user (can use the bot)\n1 - admin (can send report to the channel)\n2 - owner.')
            else:
                command, user_id, user_type = message.split(' ')
                user_id = int(user_id)
                if user_type == '0':
                    if not user_id in USER_ID:
                        USER_ID.append(user_id)
                        updateUsers(USER_ID)
                        context.bot.send_message(chat_id, 'User '+str(user_id)+' added.')
                    else:
                        context.bot.send_message(chat_id, 'User is already in the list.')
                elif user_type == '1':
                    if not user_id in ADMIN_ID:
                        ADMIN_ID.append(user_id)
                        updateAdmins(ADMIN_ID)
                        context.bot.send_message(chat_id, 'Admin '+str(user_id)+' added.')
                    else:
                        context.bot.send_message(chat_id, 'Admin is already in the list.')
                elif user_type == '2':
                    if not user_id in OWNER_ID:
                        OWNER_ID.append(user_id)
                        updateOwners(OWNER_ID)
                        context.bot.send_message(chat_id, 'Owner '+str(user_id)+' added.')
                    else:
                        context.bot.send_message(chat_id, 'Owner is already in the list.')
        except Exception:
            logging.error(traceback.format_exc())

def removeAdmin(update, context):
    chat_id = update.effective_chat.id
    message = update.message.text
    if not isOwner(chat_id):
        context.bot.send_message(chat_id, 'You are not owner. Please contact @magnusmax for an access.')
        return
    else:
        try:
            if len(re.findall(r'/rm_admin\s\d+\s[0-2]', message)) != 1:
                context.bot.send_message(chat_id, 'Bad format. Type command, id and user type separated by space, e.g. /rm_admin 123 1. User types are:\n0 - user (can use the bot)\n1 - admin (can send report to the channel)\n2 - owner.')
            else:
                command, user_id, user_type = message.split(' ')
                user_id = int(user_id)
                if user_type == '0':
                    if user_id in USER_ID:
                        USER_ID.remove(user_id)
                        updateUsers(USER_ID)
                        context.bot.send_message(chat_id, 'User '+str(user_id)+' removed.')
                    else:
                        context.bot.send_message(chat_id, 'User is not in the list.')
                elif user_type == '1':
                    if user_id in ADMIN_ID:
                        ADMIN_ID.remove(user_id)
                        updateAdmins(ADMIN_ID)
                        context.bot.send_message(chat_id, 'Admin '+str(user_id)+' removed.')
                    else:
                        context.bot.send_message(chat_id, 'Admin is not in the list.')
                elif user_type == '2':
                    if user_id in OWNER_ID:
                        OWNER_ID.remove(user_id)
                        updateOwners(OWNER_ID)
                        context.bot.send_message(chat_id, 'Owner '+str(user_id)+' removed.')
                    else:
                        context.bot.send_message(chat_id, 'Owner is not in the list.')
        except Exception:
            logging.error(traceback.format_exc())

def showAdmin(update, context):
    chat_id = update.effective_chat.id
    message = update.message.text
    if not isOwner(chat_id):
        context.bot.send_message(chat_id, 'You are not owner. Please contact @magnusmax for an access.')
        return
    else:
        try:
            if len(re.findall(r'^/show_admin\s(user|admin|owner)$', message)) != 1:
                context.bot.send_message(chat_id, 'Bad format. Type command /show_admin user|admin|owner.')
            else:
                command, user_type = message.split(' ')
                if user_type == 'user':
                    context.bot.send_message(chat_id, USER_ID)
                if user_type == 'admin':
                    context.bot.send_message(chat_id, ADMIN_ID)
                if user_type == 'owner':
                    context.bot.send_message(chat_id, OWNER_ID)
        except Exception:
            logging.error(traceback.format_exc())

start_handler = CommandHandler('start', start)
saveBattleStats_handler = MessageHandler(Filters.all, saveBattleStats)
chooseReportType_handler = MessageHandler(Filters.text, chooseReportType)
getAttackReport_handler = MessageHandler(Filters.text, getAttackReport)
getDefenceReport_handler = MessageHandler(Filters.text, getDefenceReport)
calcAttack_handler = MessageHandler(Filters.text, calcAttack)
calcDefence_handler = MessageHandler(Filters.text, calcDefence)
cancel_handler = CommandHandler('cancel', cancel)

stats_calc_conv_handler = ConversationHandler(
    entry_points = [start_handler],
    states={
        BATTLE_STATS: [saveBattleStats_handler],
        CHOOSE_REPORT_TYPE: [chooseReportType_handler],
        ATTACK_REPORT: [getAttackReport_handler],
        DEFENCE_REPORT: [getDefenceReport_handler],
        CALC_ATTACK: [calcAttack_handler],
        CALC_DEFENCE: [calcDefence_handler]

    },
    fallbacks=[cancel_handler]
)


dispatcher.add_handler(stats_calc_conv_handler)
'''
calcAttackTest_handler = MessageHandler(Filters.text, calcAttackTest)
dispatcher.add_handler(calcAttackTest_handler)
'''
report_handler = CommandHandler('report', report)
dispatcher.add_handler(report_handler)

list_handler = CommandHandler('list', listBattleStats)
dispatcher.add_handler(list_handler)

send_handler = CommandHandler('send', send)
dispatcher.add_handler(send_handler)

add_admin_handler = CommandHandler('add_admin', addAdmin)
dispatcher.add_handler(add_admin_handler)

remove_admin_handler = CommandHandler('rm_admin', removeAdmin)
dispatcher.add_handler(remove_admin_handler)

show_admin_handler = CommandHandler('show_admin', showAdmin)
dispatcher.add_handler(show_admin_handler)

msg_handler = MessageHandler(Filters.text, msg)
dispatcher.add_handler(msg_handler)

unknown_handler = MessageHandler(Filters.command, unknown)
dispatcher.add_handler(unknown_handler)

def main():
	updater.start_polling()
    #updater.idle()

if __name__ == '__main__':
    main()