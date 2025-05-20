import re
from os import environ
from pyrogram import Client, filters

from bot.helper.telegram_helper.button_build import ButtonMaker
from bot import DATABASE_CHANNEL, bot, bot_id, LOG_CHANNEL, bot_name, config_dict
from bot.helper.extra.bot_utils import new_task
from bot.database.db_file_handler import save_file, unpack_new_file_id
from pyrogram.handlers import MessageHandler
from pyrogram.filters import chat, document, video, audio
from bot.helper.telegram_helper.message_utils import process_channel
from bot.plugins.autofilter import get_poster


processed_movies = set()


media_filter = document | video | audio

@new_task
async def media(bot, message):
    """Media Handler"""
    for file_type in ("document", "video", "audio"):
        media = getattr(message, file_type, None)
        if media is not None:
            break
    media.file_type = file_type
    media.caption = message.caption
    is_saved, i = await save_file(message)
    if is_saved == True and config_dict['POST_UPDATE_CHANNEL_ID'] and config_dict['POST_CUSTOM_TEMPLATE'] is not None:
        file_id, file_ref = unpack_new_file_id(media.file_id)
        await send_movie_updates(bot, file_name=media.file_name, caption=media.caption, file_id=file_id)

async def get_imdb(file_name):
    imdb_file_name = await movie_name_format(file_name)
    imdb = await get_poster(imdb_file_name)
    if imdb:
        return imdb
    return None
    
async def movie_name_format(file_name):
  filename = re.sub(r'http\S+', '', re.sub(r'@\w+|#\w+', '', file_name).replace('_', ' ').replace('[', '').replace(']', '').replace('(', '').replace(')', '').replace('{', '').replace('}', '').replace('.', ' ').replace('@', '').replace(':', '').replace(';', '').replace("'", '').replace('-', '').replace('!', '')).strip()
  return filename

async def check_qualities(text, qualities: list):
    quality = []
    for q in qualities:
        if q in text:
            quality.append(q)
    quality = ", ".join(quality)
    return quality[:-2] if quality.endswith(", ") else quality

async def send_movie_updates(bot, file_name, caption, file_id):
    try:
        button = ButtonMaker()
        year_match = re.search(r"\b(19|20)\d{2}\b", caption)
        year = year_match.group(0) if year_match else None      
        pattern = r"(?i)(?:s|season)0*(\d{1,2})"
        season = re.search(pattern, caption)
        if not season:
            season = re.search(pattern, file_name) 
        if year:
            file_name = file_name[:file_name.find(year) + 4]      
        if not year:
            if season:
                season = season.group(1) if season else None       
                file_name = file_name[:file_name.find(season) + 1]
        qualities = ["ORG", "org", "hdcam", "HDCAM", "HQ", "hq", "HDRip", "hdrip", 
                     "camrip", "WEB-DL" "CAMRip", "hdtc", "predvd", "DVDscr", "dvdscr", 
                     "dvdrip", "dvdscr", "HDTC", "dvdscreen", "HDTS", "hdts"]
        quality = await check_qualities(caption, qualities) or "HDRip"
        language = ""
        nb_languages = [
            "Hindi", "Bengali", "English", "Marathi", 
            "Tamil", "Telugu", "Malayalam", "Kannada", 
            "Punjabi", "Gujrati", "Korean", "Japanese", 
            "Bhojpuri", "Dual", "Multi", "Urdu",
            "French", "Spanish", "German", "Italian",
            "Russian", "Chinese", "Arabic", "Thai",
            "Vietnamese", "Indonesian", "Filipino", "Malay",
            "Turkish", "Persian", "Swedish", "Norwegian",
            "Hin", "Ben", "Eng", "Mar", "Tam", "Tel",
            "Mal", "Kan", "Pun", "Guj", "Kor", "Jap",
        ]    
        for lang in nb_languages:
            if lang.lower() in caption.lower():
                if lang.lower() in ['hin', 'ben', 'eng', 'mar', 'tam', 'tel', 'mal', 'kan', 'pun', 'guj']:
                    if lang.lower() == 'hin':
                        lang = 'Hindi'
                    elif lang.lower() == 'ben':
                        lang = 'Bengali'
                    elif lang.lower() == 'eng':
                        lang = 'English'
                    elif lang.lower() == 'mar':
                        lang = 'Marathi'
                    elif lang.lower() == 'tam':
                        lang = 'Tamil'
                    elif lang.lower() == 'tel':
                        lang = 'Telugu'
                    elif lang.lower() == 'mal':
                        lang = 'Malayalam'
                    elif lang.lower() == 'kan':
                        lang = 'Kannada'
                    elif lang.lower() == 'pun':
                        lang = 'Punjabi'
                    elif lang.lower() == 'guj':
                        lang = 'Gujrati'
                    elif lang.lower() == 'kor':
                        lang = 'Korean'
                    elif lang.lower() == 'jap':
                        lang = 'Japanese'
                language += f"{lang}, "
        language = language.strip(", ") or "Not Idea"
        movie_name = await movie_name_format(file_name)    
        if movie_name in processed_movies:
            return 
        processed_movies.add(movie_name)    
        imdb = await get_imdb(movie_name)
        if imdb:
            poster_url = imdb.get('poster', None)
            distributors = imdb.get('distributors', None)
            release_date = imdb.get('release_date', None)
            rating = imdb.get('rating', None)
            genres = imdb.get('genres', None)
            year = imdb.get('year', None)
        else:
            poster_url = None
            distributors = None
            release_date = None
            rating = None
            genres = None
            year = None

        caption_message = config_dict['POST_CUSTOM_TEMPLATE'].format(
            file_name=movie_name if movie_name else '', 
            language=language if language else '', 
            quality=quality if quality else '',
            distributors=distributors if distributors else '',
            release_date=release_date if release_date else '',
            rating=rating if rating else '',
            genres=genres if genres else '',
            year=year if year else '',
        )
        search_movie = movie_name.replace(" ", '-')
        button.add_button('📂 ɢᴇᴛ ғɪʟᴇ 📂', url=f'https://telegram.me/{bot_name}?start=getfile-{search_movie}')    
        button.add_button('♻️ ʜᴏᴡ ᴛᴏ ᴅᴏᴡɴʟᴏᴀᴅ ♻️', url=config_dict['POST_HWTO_DOWNLOAD_URL'])
        
        reply_markup = button.build()
        if config_dict['POST_IMG_ENABLED']:
            if poster_url:
                await bot.send_photo(
                    config_dict['POST_UPDATE_CHANNEL_ID'], 
                    photo=poster_url, 
                    caption=caption_message, 
                    reply_markup=reply_markup
                )
            else:
                no_poster = "https://telegra.ph/file/88d845b4f8a024a71465d.jpg"
                await bot.send_photo(
                    config_dict['POST_UPDATE_CHANNEL_ID'], 
                    photo=no_poster, 
                    caption=caption_message, 
                    reply_markup=reply_markup
                )  
        else:
            await bot.send_message(
                config_dict['POST_UPDATE_CHANNEL_ID'], 
                text=caption_message, 
                reply_markup=reply_markup
            )
    except Exception as e:
        print('Failed to send movie update. Error - ', e)
        await bot.send_message(LOG_CHANNEL, f'Failed to send movie update. Error - {e}')
    

DATABASE_CHANNEL = DATABASE_CHANNEL.split()
DATABASE_CHANNEL = process_channel(DATABASE_CHANNEL)

bot.add_handler(MessageHandler(media, filters= chat(DATABASE_CHANNEL) & media_filter))
