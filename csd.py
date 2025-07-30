from email.mime import audio
import os, sys
import time
from uuid import uuid4
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InlineQueryResultCachedAudio, InputTextMessageContent, Update, ParseMode, File
from telegram.ext import MessageHandler, Filters, Updater, CommandHandler, CallbackQueryHandler, CallbackContext, InlineQueryHandler
from telegram.utils.helpers import escape_markdown
import logging
import sqlite3
import threading
import music_tag
import lyricsgenius
import requests

tutorial_file_id = 'BAACAgQAAxkBAAPfZKxIgqijHfkZ_619xnzgdnMcm68AArYQAAKHWmFRkvVImaZjmRovBA'
GN = 'YOUR GENIUS API TOKEN'
genius = lyricsgenius.Genius(GN)

#Dark Paradise has ID -1001604009257
channel = '-1001604009257'
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                     level=logging.INFO)
logger = logging.getLogger(__name__)

threads = list()

keyboardJoin = [[InlineKeyboardButton("Our Channel", url=('http://t.me/dark_paradise_p'))]]
#join_reply_markup = []
#join_reply_markup.append(InlineKeyboardMarkup(keyboardJoin))
#-----------------Log Setup-------------------------------------------------------------
def mlog(update, txt):
    if len(txt) > 200:
        txt = txt[:200] + ' . . .'
    usr = 'null'
    if update is not None:
        usr = str(update.effective_user.id) + ';' + str(update.effective_user.username)
    myear = str(time.localtime(time.time()).tm_year)
    mmonth = str(time.localtime(time.time()).tm_mon)
    mday = str(time.localtime(time.time()).tm_mday)
    if len(mmonth) == 1:
        mmonth = '0' + mmonth
    if len(mday) == 1:
        mday = '0' + mday
    file_name = "./log/"+ myear + mmonth + mday + '.txt'
    mhour = str(time.localtime(time.time()).tm_hour)
    mmin = str(time.localtime(time.time()).tm_min)
    msec = str(time.localtime(time.time()).tm_sec)
    if len(mhour) == 1:
        mhour = '0' + mhour
    if len(mmin) == 1:
        mmin = '0' + mmin
    if len(msec) == 1:
        msec = '0' + msec
    tmm = mhour + ':' + mmin + ':' + msec
    if not os.path.isfile(file_name):
        file = open(file_name, 'w')
        file.write('Starting new log at: ' + time.asctime(time.localtime(time.time())))
        file.close()
        print ('Starting new log at: ' + time.asctime(time.localtime(time.time())))
    log_write = '\n[' + tmm + '] [' + usr + ']: ' + str(txt.encode("utf-8"))
    file = open(file_name, 'a')
    file.write(log_write)
    file.close()
    print (log_write)
#-----------------Log Setup-------------------------------------------------------------

#-----------------SQLITE----------------------------------------------------------------
def user_check(update, context):
    d_Id = str(update.effective_chat.id)
    d_Uname = str(update.effective_chat.username)
    d_Fname = str(update.effective_chat.first_name)
    d_Lname = str(update.effective_chat.last_name)

    with sqlite3.connect('csd.sqlite') as conn:
        cur = conn.cursor()
        cur.execute('SELECT Id FROM Users WHERE Id = ? ', (d_Id,))
        row = cur.fetchone()
        if row is None:
            cur.execute('''INSERT INTO Users (Id, Uname, Fname, Lname, Joined, tmp1)
                    VALUES (?, ?, ?, ?, "0", "000")''', (d_Id, d_Uname, d_Fname, d_Lname))
            mlog(update, 'New User inserted to the database')
        else:
            cur.execute('UPDATE Users SET Uname = ? WHERE Id = ?', (d_Uname, d_Id))
            cur.execute('UPDATE Users SET Fname = ? WHERE Id = ?', (d_Fname, d_Id))
            cur.execute('UPDATE Users SET Lname = ? WHERE Id = ?', (d_Lname, d_Id))
        if isJoined(str(update.effective_chat.id), context):
            cur.execute('UPDATE Users SET Joined = ? WHERE Id = ?', ("1", d_Id))
        else:
            cur.execute('UPDATE Users SET Joined = ? WHERE Id = ?', ("0", d_Id))
        conn.commit()
        cur.close()

def isJoined(idfjoin, context):
    db_state = int(read_temp_value('force_join'))
    if db_state:
        isjo = context.bot.get_chat_member(channel, idfjoin)
        #print (isjo)
        allowed_types = ['creator', 'member', 'administrator']
        if str(isjo['status']) in allowed_types:
            return True
        else:
            return False
    else:
        return True

def lst_msg(update, msg_id):
    smdd = 0
    with sqlite3.connect('csd.sqlite') as conn:
        cur = conn.cursor()
        cur.execute('SELECT mid FROM Audios WHERE chat_id = ? AND start_mid = ?', (str(update.effective_user.id), msg_id))
        row = cur.fetchone()
        if row is None:
            smdd = 0
        else: smdd = int(row[0])
        conn.commit()
        cur.close()
    return smdd

def tmps(update, mode):
    smdd = 0
    with sqlite3.connect('csd.sqlite') as conn:
        cur = conn.cursor()
        if mode == 1:
            cur.execute('SELECT tmp1 FROM Users WHERE Id = ?', (str(update.effective_chat.id),))
        elif mode == 2:
            cur.execute('SELECT tmp2 FROM Users WHERE Id = ?', (str(update.effective_chat.id),))
        row = cur.fetchone()
        smdd = str(row[0])
        conn.commit()
        cur.close()
    return smdd

def set_tmps(update, value, mode):
    with sqlite3.connect('csd.sqlite') as conn:
        cur = conn.cursor()
        if mode == 1:
            cur.execute('UPDATE Users SET tmp1 = ? WHERE Id = ?', (value, str(update.effective_user.id)))
        elif mode == 2:
            cur.execute('UPDATE Users SET tmp2 = ? WHERE Id = ?', (value, str(update.effective_user.id)))
        conn.commit()
        cur.close()

def get_ta(update, mid):
    title = ""
    artist = ""
    f_id = ""
    with sqlite3.connect('csd.sqlite') as conn:
        cur = conn.cursor()
        cur.execute('SELECT title FROM Audios WHERE chat_id = ? AND start_mid = ?', (update.effective_chat.id, mid))
        row = cur.fetchone()
        title = str(row[0])
        cur.execute('SELECT artist FROM Audios WHERE chat_id = ? AND start_mid = ?', (update.effective_chat.id, mid))
        row = cur.fetchone()
        artist = str(row[0])
        cur.execute('SELECT file_id FROM Audios WHERE chat_id = ? AND start_mid = ?', (update.effective_chat.id, mid))
        row = cur.fetchone()
        f_id = str(row[0])
        conn.commit()
        cur.close()
    return f_id , title , artist

def song_keyboard(clb, lrcs = ""):
    skeyboard = [
                    [InlineKeyboardButton("Search and send Lyrics", switch_inline_query = lrcs)],
                    [InlineKeyboardButton("Change Title", callback_data=clb + "001")],
                    [InlineKeyboardButton("Change Artist", callback_data=clb + "002")],
                    [InlineKeyboardButton("Download the song", callback_data=clb + "003")],
                    [InlineKeyboardButton("Use Genius tags and download the song", callback_data=clb + "004")]]
    reply_markup = InlineKeyboardMarkup(skeyboard)
    return reply_markup
    
def name_check(ttxt, mode): #1 for title, 2 for artist
    if len(ttxt) > 0 and len(ttxt) < 56 and '\n' not in ttxt:
        return True
    else:
        return False

def send_song(update):
    mid = tmps(update, 2)
    f_id , title , artist = get_ta(update, mid)
    clb = new_mid(update, mid)
    tstt = txt_to_markdown(title)
    tsta = txt_to_markdown(artist)
    satxt = '''*Title* \(tap to copy\):\n`{}`\n\n*Artist* \(tap to copy\):\n`{}`'''.format(tstt, tsta)
    satxt += "\n\n*Last button will set the Song Cover and add Lyrics to the Song File automatically\.*"
    update.message.reply_audio( audio = f_id, caption = satxt, reply_markup=song_keyboard(clb, artist + ' - ' + title), parse_mode=ParseMode.MARKDOWN_V2)

def set_song_value(update, value, mode): #1 for title , 2 for artist
    mid = tmps(update, 2)
    with sqlite3.connect('csd.sqlite') as conn:
        cur = conn.cursor()
        if mode == 1:
            cur.execute('UPDATE Audios SET title = ? WHERE chat_id = ? AND start_mid = ?', (value, str(update.effective_user.id), mid))
        elif mode == 2:
            cur.execute('UPDATE Audios SET artist = ? WHERE chat_id = ? AND start_mid = ?', (value, str(update.effective_user.id), mid))
        conn.commit()
        cur.close()

def new_mid(update, mid):
    clb = str(mid) + "$" + str(update.message.message_id) + "&"
    with sqlite3.connect('csd.sqlite') as conn:
        cur = conn.cursor()
        cur.execute('UPDATE Audios SET mid = ? WHERE chat_id = ? AND start_mid = ?', (str(update.message.message_id), str(update.effective_user.id), mid))
        conn.commit()
        cur.close()
    return clb

def download_send_song(update, context, mid, prd):
    fid = ""
    fname = ""
    title = ""
    artist = ""
    dur = 0
    with sqlite3.connect('csd.sqlite') as conn:
        cur = conn.cursor()
        cur.execute('UPDATE Audios SET mid = ? WHERE chat_id = ? AND start_mid = ?', (str(0), str(update.effective_user.id), mid))
        cur.execute('SELECT file_id FROM Audios WHERE chat_id = ? AND start_mid = ?', (update.effective_user.id, mid))
        row = cur.fetchone()
        fid = str(row[0]) 
        cur.execute('SELECT file_name FROM Audios WHERE chat_id = ? AND start_mid = ?', (update.effective_user.id, mid))
        row = cur.fetchone()
        fname = str(row[0]) 
        cur.execute('SELECT title FROM Audios WHERE chat_id = ? AND start_mid = ?', (update.effective_user.id, mid))
        row = cur.fetchone()
        title = str(row[0]) 
        cur.execute('SELECT artist FROM Audios WHERE chat_id = ? AND start_mid = ?', (update.effective_user.id, mid))
        row = cur.fetchone()
        artist = str(row[0]) 
        cur.execute('SELECT dur FROM Audios WHERE chat_id = ? AND start_mid = ?', (update.effective_user.id, mid))
        row = cur.fetchone()
        dur = str(row[0]) 
        conn.commit()
        cur.close()
    mlog(update, "Download and Send Song to the user: {} - {} with the file name: {}".format(artist, title, fname))
    pat = "./files/" + str(update.effective_user.id)
    if not os.path.isdir("./files"):
        os.mkdir("./files")
    if not os.path.isdir(pat):
        os.mkdir(pat)
    pat += "/" + str(mid)
    midpath = pat
    if not os.path.isdir(pat):
        os.mkdir(pat)
    pat += "/"
    thm = pat + 'thumb.jpg'
    pat += str(fname)
    ffi = context.bot.get_file(fid)
    ffi.download(pat)
    #pat += str(fname)

    #https://pypi.org/project/music-tag/
    fmu = music_tag.load_file(pat)
    fmu['title'] = title
    fmu['album artist'] = artist
    fmu['Artist'] = artist
    sthumb = None
    if prd == '004':
        song = genius.search_song(artist + ' - ' + title, get_full_info=True)
        if song:
            #thumb_url=song.header_image_thumbnail_url
            thumb_url = ""
            thumb_url=song.header_image_url
            if "https://images.genius.com" not in thumb_url:
                thumb_url = song.song_art_image_thumbnail_url
            #thumb_url=song.song_art_image_thumbnail_url
            if "https://images.genius.com" in thumb_url:
                response = requests.get(thumb_url)
                with open(thm, "wb") as thubi:
                    thubi.write(response.content)
                with open(thm, 'rb') as img_in:
                    fmu['artwork'] = img_in.read()
                    sthumb = img_in.read()
            full_lyric = text_format(song, forfile=True)
            fmu['lyrics'] = full_lyric
            mlog(update, "Lyrics and Artwork Done.")
    #lngh = fmu.length 
    #print(fmu)
    fmu.save()
    context.bot.send_message(chat_id=update.effective_user.id, text="Uploading file to telegram. . .")
    context.bot.send_audio(chat_id=update.effective_user.id, duration = dur, performer = artist, title = title, audio = open(pat, 'rb'), thumb = sthumb)
    if os.path.exists(pat):
        os.remove(pat)
    if os.path.exists(thm):
        os.remove(thm)
    if os.path.isdir(midpath):
        os.rmdir(midpath)

def all_temp_values():
    fid = ""
    with sqlite3.connect('csd.sqlite') as conn:
        cur = conn.cursor()
        cur.execute('SELECT * FROM Temp_values')
        row = cur.fetchall()
        fid = str(row) 
        conn.commit()
        cur.close()
    return fid

def set_temp_value(v_name, v_value):
    with sqlite3.connect('csd.sqlite') as conn:
        cur = conn.cursor()
        cur.execute('UPDATE Temp_values SET v_value = ? WHERE v_name = ?', (v_value, v_name))
        conn.commit()
        cur.close()

def read_temp_value(v_name):
    fid = ""
    with sqlite3.connect('csd.sqlite') as conn:
        cur = conn.cursor()
        cur.execute('SELECT v_value FROM Temp_values WHERE v_name = ?', (v_name, ))
        row = cur.fetchone()
        fid = str(row[0]) 
        conn.commit()
        cur.close()
    return fid

def sond_num():
    rd = 0
    with sqlite3.connect('csd.sqlite') as conn:
        cur = conn.cursor()
        cur.execute('SELECT v_value FROM Temp_values WHERE v_name = ?', ("song_num", ))
        row = cur.fetchone()
        fid = str(row[0]) 
        rd = int(fid)
        cur.execute('UPDATE Temp_values SET v_value = ? WHERE v_name = ?', (str(rd + 1), "song_num"))
        conn.commit()
        cur.close()
    return rd

def check_song(capin):
    row = None
    with sqlite3.connect('csd.sqlite') as conn:
        cur = conn.cursor()
        cur.execute('SELECT * FROM Audios WHERE caption = ?', (capin, ))
        row = cur.fetchone()
        conn.commit()
        cur.close()
    return row

#----------------------------------------------------------------

plz_join_text = "Please join our channel to use the bot👇"
lyricstnx = "Thanks for using Song Tag to find Lyrics :)"
stxtx = "🔰Song Tag is a Telegram Bot helps you change wrong song tags. You can change song covers automatically. In inline mode, Bot helps you find Lyrics. Song Tag also helps you send songs in reply to other messages in a chat.\n✔️Join our channel: @dark_paradise_p\n📞Contact: @imParsaMZ\n==============================\n🔰بات Song Tag به شما کمک می‌کند تگ‌های اشتباه آهنگ را تغییر دهید. همچنین می‌توانید به صورت خودکار، کاور آهنگ‌ها درست کنید. در حالت inline، می‌توانید متن آهنگ‌ها را پیدا کنید. همچنین بات Song Tag به شما کمک می‌کند آهنگ‌ها را به صورت ریپلای به بقیه افراد در چت‌ها بفرستید.\n✔️کانال ما: @dark_paradise_p\n📞پشتیبانی: @imParsaMZ"
star_key = [[InlineKeyboardButton("🎵 Search and send Lyrics 🎵", switch_inline_query="")]]
def start(update: Update, context: CallbackContext) -> None:
    user_check(update, context)
    mlog(update ,update.message.text)
    #update.message.reply_text( text=stxtx, reply_markup=InlineKeyboardMarkup(star_key))
    update.message.reply_video(caption=stxtx, video=tutorial_file_id, reply_markup=InlineKeyboardMarkup(star_key))

def txt_to_markdown(tx):
    txy = str(tx)
    txy = txy.replace('\\', '\\')
    txy = txy.replace('+', '\+')
    txy = txy.replace('-', '\-')
    txy = txy.replace('|', '\|')
    txy = txy.replace('(', '\(')
    txy = txy.replace(')', '\)')
    txy = txy.replace('.', '\.')
    txy = txy.replace('_', '\_')
    txy = txy.replace('!', '\!')
    txy = txy.replace("`", "\`")
    txy = txy.replace('#', '\#')
    #txy = txy.replace('*', '\*')
    txy = txy.replace('<', '\<')
    txy = txy.replace('>', '\>')
    txy = txy.replace('[', '\[')
    txy = txy.replace(']', '\]')
    txy = txy.replace('{', '\{')
    txy = txy.replace('}', '\}')
    return txy

def maintxt(update: Update, context: CallbackContext) -> None:
    user_check(update, context)
    mlog(update, update.message.text)
    mtxt = update.message.text
    state_u = tmps(update,1)
    if isJoined(str(update.effective_chat.id), context):
        if mtxt.startswith('/start'):
            #update.message.reply_text( text=stxtx, reply_markup=InlineKeyboardMarkup(star_key))
            update.message.reply_video(caption=stxtx, video=tutorial_file_id, reply_markup=InlineKeyboardMarkup(star_key))
            set_tmps(update,'000',1)        
        elif state_u == '001':
            if mtxt.lower().startswith('/skip'):
                set_tmps(update, '000',1)
                send_song(update)
            else:
                if name_check(mtxt, 1):
                    set_song_value(update, mtxt, 1)
                    set_tmps(update, '000',1)
                    update.message.reply_text(text = "Done✅")
                    send_song(update)
                else:
                    update.message.reply_text(text = "The title is incorrect!")
                    set_tmps(update, '000',1)
                    send_song(update)

        elif state_u == '002':
            if mtxt.lower().startswith('/skip'):
                set_tmps(update, '000',1)
                send_song(update)
            else:
                if name_check(mtxt, 1):
                    set_song_value(update, mtxt, 2)
                    set_tmps(update, '000',1)
                    update.message.reply_text(text = "Done✅")
                    send_song(update)
                else:
                    update.message.reply_text(text = "The artist is incorrect!")
                    set_tmps(update, '000',1)
                    send_song(update)
        elif ('Join Our channel:' in mtxt) and ('@dark_paradise_p' in mtxt):
            update.message.reply_text(text=lyricstnx)
        else:
            set_tmps(update, '000', 1)
            #update.message.reply_text( text=stxtx, reply_markup=InlineKeyboardMarkup(star_key))
            update.message.reply_video(caption=stxtx, video=tutorial_file_id, reply_markup=InlineKeyboardMarkup(star_key))
    else:
        update.message.reply_text( text = plz_join_text, reply_markup = InlineKeyboardMarkup(keyboardJoin))

def mainaudio(update: Update, context: CallbackContext) -> None:
    user_check(update, context)
    msd = update.message.audio
    mfile_id = msd.file_id
    capin = "a{0}{1}a{2}".format(str(update.message.message_id), mfile_id[-10:], sond_num())
    mlog(update, "Audio file with id: " + mfile_id)
    #print(update.message.audio)
    if isJoined(str(update.effective_chat.id), context):
        set_tmps(update, '000', 1)
        #if msd.file_size < 20000000:
        if 1:
            with sqlite3.connect('csd.sqlite') as conn:
                cur = conn.cursor()
                ttile = msd.title
                ttart = msd.performer
                dur = msd.duration
                if not ttile: ttile = 'Unknown'
                if not ttart: ttart = 'Unknown'
                cur.execute('''INSERT INTO Audios (chat_id, file_id, start_mid, mid, caption, title, artist, open, file_name, dur)
                        VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)''', 
                        (update.effective_chat.id, mfile_id, str(update.message.message_id), str(update.message.message_id), capin, ttile, ttart, msd.file_name, dur))
                conn.commit()
                cur.close()
            clb = str(update.message.message_id) + "$" + str(update.message.message_id) + "&"
            skeyboard = [[InlineKeyboardButton("Search and send Lyrics", switch_inline_query = ttart + ' - ' + ttile)]]
            skeyboard.append([InlineKeyboardButton("Send to other chats", switch_inline_query = capin)])
            tstt = txt_to_markdown(ttile)
            tsta = txt_to_markdown(ttart)
            capint = txt_to_markdown(capin)
            satxt = '''*Title* \(tap to copy\):\n`{}`\n\n*Artist* \(tap to copy\):\n`{}`\n\n*Inline Query* \(You can place this text in the chatbox to send the song\):\n`{}`'''.format(tstt, tsta, "@Songdetailbot " + capint)
            if msd.file_size < 20000000:
                skeyboard.append([InlineKeyboardButton("Change Title", callback_data=clb + "001")])
                skeyboard.append([InlineKeyboardButton("Change Artist", callback_data=clb + "002")])
                skeyboard.append([InlineKeyboardButton("Use Genius tags and download the song", callback_data=clb + "004")])
                satxt += "\n\n*Last button will set the Song Cover and add Lyrics to the Song File automatically\.*"
            else:
                satxt = satxt + "\n\nTo change the tags, file size should be less than 20MB\!"
            reply_markup = InlineKeyboardMarkup(skeyboard)
            update.message.reply_audio( audio = mfile_id, caption = satxt, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN_V2)
        
    else:
        update.message.reply_text( text = plz_join_text, reply_markup = InlineKeyboardMarkup(keyboardJoin))

def inline_button(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    ls_index = str(query.data).find('$')
    ls2_index = str(query.data).find('&')
    msg_id = int(str(query.data)[:ls_index])
    midd = lst_msg(update, msg_id)
    mid_id = int(str(query.data)[ls_index+1:ls2_index])
    if midd == mid_id:
        prd = (str(query.data)[ls2_index+1:])
        if prd == '001':
            context.bot.send_message(chat_id=update.effective_user.id, text="Send the new title. Send /skip to skip.")
            set_tmps(update, '001', 1)
            set_tmps(update, str(msg_id), 2)
        elif prd == '002':
            context.bot.send_message(chat_id=update.effective_user.id, text="Send the new artist. Send /skip to skip.")
            set_tmps(update, '002', 1)
            set_tmps(update, str(msg_id), 2)
        else: #003 - Done
            query.edit_message_caption(caption="Dowloading. . .")
            set_tmps(update, '000', 1)
            x = threading.Thread(target=download_send_song, args=(update, context, str(msg_id), prd))
            threads.append(x)
            x.start()
    else:
        #query.edit_message_text(text="⚠️ This message is not accessible anymore! ⚠️")
        query.edit_message_caption(caption="⚠️ The message is not accessible anymore! ⚠️")

def find_nline(txtln):
    fnln = 1
    while txtln[(-1)*fnln] != '\n':
        fnln = fnln + 1
    return fnln

def text_format(song_l, forfile = False):
    song_lyric = ""
    #song_lyric.replace()
    song_lyric = str(song_l.lyrics)
    s = song_lyric.find("Lyrics")
    if s != -1: song_lyric = song_lyric[s+6:]
    ftm = "🎵 *{0}* - *{1}*\n\n".format(song_l.artist, song_l.title)
    if forfile == False:
        song_lyric = ftm + song_lyric
        song_lyric = song_lyric.replace('[', '⏺ *')
        song_lyric = song_lyric.replace(']', '*')
        song_lyric = txt_to_markdown(song_lyric)
    song_lyric = song_lyric.replace('You might also like', '')
    if song_lyric.endswith("Embed"):
        song_lyric = song_lyric[:-5]
        while song_lyric[-1].isnumeric(): song_lyric = song_lyric[:-1]
    return song_lyric

def inlinequery(update, context):
    query = ""
    query = update.inline_query.query
    query = query.strip()
    if query == "":
        return
    mlog(update ,' [Inline Query]: ' + query) 
    #songs = genius.search_songs(query, per_page=2)
    results = []
    chs = check_song(query)
    if chs:
        results.append(InlineQueryResultCachedAudio(id=str(uuid4()), audio_file_id=chs[1], 
                                                    caption="[Song Tag](https://t.me/Songdetailbot)",
                                                    parse_mode=ParseMode.MARKDOWN_V2))
    else:
        song = genius.search_song(query, get_full_info=True)
        if(song):
            song_details = "*{0}* by *{1}*\n\n{2}".format(song.title, song.artist, song.url)
            song_details = txt_to_markdown(song_details)
            results.append(InlineQueryResultArticle(id=str(uuid4()),
                title = song.artist + ' - ' + song.title,
                description = 'Song Details',
                input_message_content=InputTextMessageContent(
                song_details, parse_mode=ParseMode.MARKDOWN_V2),
                thumb_url=song.header_image_thumbnail_url))
            full_lyric = text_format(song)
            end_of_the_lyrics = '\n\nJoin Our channel:\n🎵 *@dark\_paradise\_p* 🎵'
            lyrics_parts = 1
            while len(full_lyric) > 3900:
                nl_index = find_nline(full_lyric[:3500])
                this_part_lyrics = 'Lyrics Part ' + str(lyrics_parts) + '\n\n' + full_lyric[:3501-nl_index]
                full_lyric = full_lyric[3501-nl_index:]
                this_part_lyrics = this_part_lyrics + end_of_the_lyrics
                results.append(InlineQueryResultArticle(id=str(uuid4()),
                    title = 'Lyrics Part ' + str(lyrics_parts),
                    input_message_content=InputTextMessageContent(
                    this_part_lyrics, parse_mode=ParseMode.MARKDOWN_V2),
                    thumb_url=song.song_art_image_thumbnail_url))
                lyrics_parts = lyrics_parts + 1
            full_lyric = full_lyric + end_of_the_lyrics
            if lyrics_parts == 1:
                results.append(InlineQueryResultArticle(id=str(uuid4()),
                    title = 'Lyrics',
                    input_message_content=InputTextMessageContent(
                    full_lyric, parse_mode=ParseMode.MARKDOWN_V2),
                    thumb_url=song.song_art_image_thumbnail_url))
            else: 
                full_lyric = 'Lyrics Part ' + str(lyrics_parts) + '\n\n' + full_lyric
                results.append(InlineQueryResultArticle(id=str(uuid4()),
                    title = 'Lyrics Part ' + str(lyrics_parts),
                    input_message_content=InputTextMessageContent(
                    full_lyric, parse_mode=ParseMode.MARKDOWN_V2),
                    thumb_url=song.song_art_image_thumbnail_url))
        
        else:
            results.append(InlineQueryResultArticle(id=str(uuid4()),
                title= "Can't find anything",
                input_message_content=InputTextMessageContent(
                ("Can't find anything\. Trying different keywords may help\."), parse_mode=ParseMode.MARKDOWN_V2)))
    update.inline_query.answer(results)


def main():
    updater = Updater(token='TELEGRAM BOT API TOKEN', use_context=True)
    updater.dispatcher.add_handler(InlineQueryHandler(inlinequery))
    updater.dispatcher.add_handler(MessageHandler(Filters.text, maintxt))
    updater.dispatcher.add_handler(CallbackQueryHandler(inline_button))
    updater.dispatcher.add_handler(MessageHandler(Filters.audio, mainaudio))
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()

