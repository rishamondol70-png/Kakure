#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎬 CINEFLIX ULTIMATE BOT
Premium Video Bot with Full Admin Panel
"""

import os
import sys
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    CallbackQueryHandler,
    ConversationHandler
)
from telegram.constants import ParseMode
from telegram.error import BadRequest, TelegramError
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure

# ===================== CONFIGURATION =====================
# All sensitive data from environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
ADMIN_ID = os.getenv("ADMIN_ID")

# Validate required environment variables
if not BOT_TOKEN:
    print("❌ ERROR: BOT_TOKEN environment variable not set!")
    sys.exit(1)

if not MONGO_URI:
    print("❌ ERROR: MONGO_URI environment variable not set!")
    sys.exit(1)

if not ADMIN_ID:
    print("❌ ERROR: ADMIN_ID environment variable not set!")
    sys.exit(1)

try:
    ADMIN_ID = int(ADMIN_ID)
except ValueError:
    print("❌ ERROR: ADMIN_ID must be a number!")
    sys.exit(1)

# ===================== LOGGING SETUP =====================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===================== MONGODB SETUP =====================
try:
    logger.info("🔄 Connecting to MongoDB...")
    mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    mongo_client.server_info()
    db = mongo_client['cineflix_bot']
    
    # Collections
    videos_col = db['videos']
    channels_col = db['channels']
    force_join_col = db['force_join_channels']
    users_col = db['users']
    settings_col = db['settings']
    messages_col = db['messages']
    
    logger.info("✅ MongoDB Connected Successfully!")
    
except (ConnectionFailure, OperationFailure) as e:
    logger.error(f"❌ MongoDB Connection Failed: {e}")
    logger.error("Bot cannot run without database. Please check MONGO_URI.")
    sys.exit(1)

# ===================== CONVERSATION STATES =====================
EDITING_MESSAGE = 1
ADDING_CHANNEL = 2
EDITING_SETTING = 3

# Admin state tracking
admin_states = {}

# ===================== DEFAULT MESSAGES =====================
DEFAULT_MESSAGES = {
    'welcome': """🎬 **স্বাগতম CINEFLIX এ!**
**Welcome to CINEFLIX!**

Hello **{name}**! 👋

আপনার সব পছন্দের Movies, Series এবং Exclusive Content এক জায়গায়!
All your favorite Movies, Series, and Exclusive Content in one place!

**🚀 কীভাবে ভিডিও দেখবেন?**
**🚀 How to Watch Videos?**

১. নিচে "🎮 Open CINEFLIX App" ক্লিক করুন
2. পছন্দের ভিডিও সিলেক্ট করুন
3. Watch Now ক্লিক করুন
4. Enjoy! 🍿

**📢 Important:**
✅ সব কন্টেন্ট আনলক করতে আমাদের চ্যানেল জয়েন করুন
✅ Premium quality HD videos
✅ প্রতিদিন নতুন আপডেট

Happy Streaming! 🎉""",

    'help': """📚 **CINEFLIX Bot - Help Guide**
📚 **CINEFLIX Bot - সাহায্য গাইড**

**🎯 Commands / কমান্ড:**
/start - বোট শুরু করুন | Start bot
/help - সাহায্য দেখুন | Show help

**🎬 কীভাবে ভিডিও দেখবেন?**
**🎬 How to watch videos?**

**Step 1:** /start দিয়ে Mini App খুলুন
**Step 2:** পছন্দের ভিডিও সিলেক্ট করুন
**Step 3:** চ্যানেল জয়েন করুন (যদি বলা হয়)
**Step 4:** ভিডিও উপভোগ করুন! 🍿

**⚠️ সমস্যা? Having issues?**
- ভিডিও না দেখা গেলে চ্যানেল জয়েন করুন
- লিঙ্ক কাজ না করলে Mini App রিফ্রেশ করুন
- অন্য সমস্যায় Admin কে মেসেজ করুন""",

    'force_join': """🔒 **Content Locked! কন্টেন্ট লক!**

এই ভিডিও দেখতে হলে আমাদের চ্যানেলগুলোতে জয়েন করতে হবে!
To watch this video, you need to join our channels!

**📢 Steps / ধাপসমূহ:**

১. নিচের সব চ্যানেলে "Join Channel" বাটন ক্লিক করুন
2. সব চ্যানেলে জয়েন করুন
3. "✅ Joined - Unlock Video" ক্লিক করুন

After joining, you'll get instant access! 🎉
জয়েন করার পর সাথে সাথে ভিডিও পাবেন! 🎉""",

    'after_video': """🎬 **আরও ভিডিও দেখতে চান?**
🎬 **Want to watch more videos?**

👉 আমাদের Mini App এ ফিরে যান এবং হাজারো ভিডিও উপভোগ করুন!
👉 Go back to our Mini App and enjoy thousands of videos!

📺 প্রতিদিন নতুন কন্টেন্ট আপডেট হয়! 🔥
📺 New content updated daily! 🔥

⭐ Best experience এর জন্য Mini App ব্যবহার করুন!
⭐ Use Mini App for the best experience!""",

    'video_not_found': """❌ **দুঃখিত! Video Not Found!**

এই ভিডিওটি আর পাওয়া যাচ্ছে না বা লিঙ্ক ভুল।
This video is no longer available or the link is incorrect.

**কী করবেন? What to do?**

✅ Mini App এ ফিরে অন্য ভিডিও দেখুন
✅ Go back to Mini App and watch other videos

✅ আমাদের চ্যানেলে জয়েন থাকুন — প্রতিদিন নতুন কন্টেন্ট!
✅ Stay joined to our channel — new content daily!"""
}

DEFAULT_SETTINGS = {
    'mini_app_url': 'https://cinaflix-streaming.vercel.app/',
    'main_channel_id': -1003872857468,
    'main_channel_username': 'Cinaflixsteem',
    'video_protection': True,
    'bot_name': 'CINEFLIX'
}

# ===================== DATABASE HELPER FUNCTIONS =====================

def get_setting(key, default=None):
    """Get setting from database"""
    try:
        setting = settings_col.find_one({'key': key})
        return setting['value'] if setting else default
    except Exception as e:
        logger.error(f"Error getting setting {key}: {e}")
        return default

def set_setting(key, value):
    """Set setting in database"""
    try:
        settings_col.update_one(
            {'key': key},
            {'$set': {'key': key, 'value': value, 'updated_at': datetime.utcnow()}},
            upsert=True
        )
        return True
    except Exception as e:
        logger.error(f"Error setting {key}: {e}")
        return False

def get_message(key):
    """Get message template from database"""
    try:
        msg = messages_col.find_one({'key': key})
        return msg['text'] if msg else DEFAULT_MESSAGES.get(key, '')
    except Exception as e:
        logger.error(f"Error getting message {key}: {e}")
        return DEFAULT_MESSAGES.get(key, '')

def set_message(key, text):
    """Set message template in database"""
    try:
        messages_col.update_one(
            {'key': key},
            {'$set': {'key': key, 'text': text, 'updated_at': datetime.utcnow()}},
            upsert=True
        )
        return True
    except Exception as e:
        logger.error(f"Error setting message {key}: {e}")
        return False

def initialize_defaults():
    """Initialize default settings and messages if not exists"""
    try:
        # Initialize settings
        for key, value in DEFAULT_SETTINGS.items():
            if not settings_col.find_one({'key': key}):
                set_setting(key, value)
        
        # Initialize messages
        for key, text in DEFAULT_MESSAGES.items():
            if not messages_col.find_one({'key': key}):
                set_message(key, text)
        
        logger.info("✅ Default settings and messages initialized")
    except Exception as e:
        logger.error(f"Error initializing defaults: {e}")

def save_video(channel_id, message_id, channel_name="Main"):
    """Save video to database"""
    try:
        video_data = {
            'channel_id': channel_id,
            'message_id': message_id,
            'channel_name': channel_name,
            'saved_at': datetime.utcnow(),
            'views': 0
        }
        videos_col.update_one(
            {'channel_id': channel_id, 'message_id': message_id},
            {'$set': video_data},
            upsert=True
        )
        logger.info(f"✅ Video saved: {channel_name} - {message_id}")
        return True
    except Exception as e:
        logger.error(f"Error saving video: {e}")
        return False

def get_video(message_id):
    """Get video from database"""
    try:
        return videos_col.find_one({'message_id': int(message_id)})
    except Exception as e:
        logger.error(f"Error getting video: {e}")
        return None

def increment_video_view(message_id):
    """Increment video view count"""
    try:
        videos_col.update_one(
            {'message_id': int(message_id)},
            {'$inc': {'views': 1}}
        )
    except Exception as e:
        logger.error(f"Error incrementing view: {e}")

def add_force_join_channel(channel_id, username):
    """Add force join channel"""
    try:
        channel_data = {
            'channel_id': channel_id,
            'username': username.replace('@', ''),
            'added_at': datetime.utcnow(),
            'is_active': True
        }
        force_join_col.update_one(
            {'channel_id': channel_id},
            {'$set': channel_data},
            upsert=True
        )
        logger.info(f"✅ Force join channel added: @{username}")
        return True
    except Exception as e:
        logger.error(f"Error adding force join channel: {e}")
        return False

def remove_force_join_channel(channel_id):
    """Remove force join channel"""
    try:
        result = force_join_col.delete_one({'channel_id': channel_id})
        return result.deleted_count > 0
    except Exception as e:
        logger.error(f"Error removing force join channel: {e}")
        return False

def get_force_join_channels():
    """Get all active force join channels"""
    try:
        return list(force_join_col.find({'is_active': True}))
    except Exception as e:
        logger.error(f"Error getting force join channels: {e}")
        return []

def save_user(user_id, username, first_name):
    """Save user to database"""
    try:
        user_data = {
            'user_id': user_id,
            'username': username,
            'first_name': first_name,
            'last_active': datetime.utcnow()
        }
        users_col.update_one(
            {'user_id': user_id},
            {'$set': user_data, '$setOnInsert': {'first_seen': datetime.utcnow()}},
            upsert=True
        )
    except Exception as e:
        logger.error(f"Error saving user: {e}")

def get_stats():
    """Get bot statistics"""
    try:
        return {
            'users': users_col.count_documents({}),
            'videos': videos_col.count_documents({}),
            'force_join': force_join_col.count_documents({'is_active': True})
        }
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return {'users': 0, 'videos': 0, 'force_join': 0}

# ===================== ADMIN PANEL KEYBOARDS =====================

def admin_main_keyboard():
    """Main admin panel keyboard"""
    keyboard = [
        [
            InlineKeyboardButton("📺 Channel Manager", callback_data="admin_channels"),
            InlineKeyboardButton("📝 Edit Messages", callback_data="admin_messages")
        ],
        [
            InlineKeyboardButton("⚙️ Settings", callback_data="admin_settings"),
            InlineKeyboardButton("📊 Statistics", callback_data="admin_stats")
        ],
        [
            InlineKeyboardButton("🔄 Refresh", callback_data="admin_refresh"),
            InlineKeyboardButton("❌ Close", callback_data="admin_close")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def channel_manager_keyboard():
    """Channel manager keyboard"""
    channels = get_force_join_channels()
    keyboard = []
    
    for ch in channels:
        keyboard.append([
            InlineKeyboardButton(
                f"📢 @{ch['username']}", 
                callback_data=f"view_channel_{ch['channel_id']}"
            ),
            InlineKeyboardButton(
                "❌ Remove", 
                callback_data=f"remove_channel_{ch['channel_id']}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("➕ Add New Channel", callback_data="add_channel")])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="admin_main")])
    
    return InlineKeyboardMarkup(keyboard)

def message_editor_keyboard():
    """Message editor keyboard"""
    keyboard = [
        [InlineKeyboardButton("✏️ Welcome Message", callback_data="edit_msg_welcome")],
        [InlineKeyboardButton("✏️ Help Message", callback_data="edit_msg_help")],
        [InlineKeyboardButton("✏️ Force Join Message", callback_data="edit_msg_force_join")],
        [InlineKeyboardButton("✏️ After Video Message", callback_data="edit_msg_after_video")],
        [InlineKeyboardButton("✏️ Video Not Found Message", callback_data="edit_msg_video_not_found")],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def settings_keyboard():
    """Settings keyboard"""
    keyboard = [
        [InlineKeyboardButton("🎮 Mini App URL", callback_data="setting_mini_app")],
        [InlineKeyboardButton("📢 Main Channel", callback_data="setting_main_channel")],
        [InlineKeyboardButton("🔒 Video Protection", callback_data="setting_protection")],
        [InlineKeyboardButton("🤖 Bot Name", callback_data="setting_bot_name")],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ===================== START COMMAND =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    save_user(user.id, user.username, user.first_name)
    
    # Check for video deep link
    if context.args and len(context.args) > 0:
        video_id = context.args[0]
        await handle_video_request(update, context, video_id)
        return
    
    # Get settings
    mini_app_url = get_setting('mini_app_url', DEFAULT_SETTINGS['mini_app_url'])
    main_channel = get_setting('main_channel_username', DEFAULT_SETTINGS['main_channel_username'])
    
    # Welcome message
    keyboard = [
        [InlineKeyboardButton("🎮 Open CINEFLIX App", web_app={"url": mini_app_url})],
        [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{main_channel}")],
        [InlineKeyboardButton("❓ Help", callback_data="help")]
    ]
    
    welcome_text = get_message('welcome').format(name=user.first_name)
    
    try:
        await update.message.reply_text(
            welcome_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        logger.error(f"Error sending welcome message: {e}")

# ===================== VIDEO REQUEST HANDLER =====================
async def handle_video_request(update: Update, context: ContextTypes.DEFAULT_TYPE, video_id: str):
    """Handle video playback request"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    try:
        message_id = int(video_id)
    except ValueError:
        await update.message.reply_text(
            get_message('video_not_found'),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Get video from database
    video = get_video(message_id)
    if not video:
        await update.message.reply_text(
            get_message('video_not_found'),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Check force join channels
    force_channels = get_force_join_channels()
    not_joined = []
    
    for channel in force_channels:
        try:
            member = await context.bot.get_chat_member(channel['channel_id'], user.id)
            if member.status in ['left', 'kicked']:
                not_joined.append(channel)
        except Exception as e:
            logger.error(f"Error checking membership: {e}")
            not_joined.append(channel)
    
    if not_joined:
        # User hasn't joined all channels
        keyboard = []
        for ch in not_joined:
            keyboard.append([InlineKeyboardButton(
                f"📢 Join @{ch['username']}", 
                url=f"https://t.me/{ch['username']}"
            )])
        keyboard.append([InlineKeyboardButton(
            "✅ Joined - Unlock Video", 
            callback_data=f"verify_{video_id}"
        )])
        
        await update.message.reply_text(
            get_message('force_join'),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # User joined all channels - send video
    try:
        protect = get_setting('video_protection', True)
        
        await context.bot.copy_message(
            chat_id=chat_id,
            from_chat_id=video['channel_id'],
            message_id=message_id,
            protect_content=protect
        )
        
        increment_video_view(message_id)
        
        # After video message
        mini_app_url = get_setting('mini_app_url', DEFAULT_SETTINGS['mini_app_url'])
        keyboard = [[InlineKeyboardButton("🔙 Back to App", web_app={"url": mini_app_url})]]
        
        await update.message.reply_text(
            get_message('after_video'),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
        
        logger.info(f"✅ Video sent to user {user.id}: {message_id}")
        
    except BadRequest as e:
        if "message to copy not found" in str(e).lower():
            await update.message.reply_text(
                get_message('video_not_found'),
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            logger.error(f"Error sending video: {e}")

# ===================== CALLBACK QUERY HANDLER =====================
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    # Help button
    if data == "help":
        await query.message.reply_text(
            get_message('help'),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Video verification
    if data.startswith("verify_"):
        video_id = data.replace("verify_", "")
        update.message = query.message
        await handle_video_request(update, context, video_id)
        return
    
    # Admin only from here
    if user_id != ADMIN_ID:
        await query.answer("⛔ Admin only!", show_alert=True)
        return
    
    # Admin panel navigation
    if data == "admin_main":
        stats = get_stats()
        text = f"""🔧 **CINEFLIX ADMIN PANEL**

📊 **Statistics:**
👥 Users: {stats['users']}
📹 Videos: {stats['videos']}
🔒 Force Join: {stats['force_join']}

Select an option below:"""
        
        await query.edit_message_text(
            text,
            reply_markup=admin_main_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data == "admin_channels":
        await query.edit_message_text(
            "📺 **Channel Manager**\n\nManage force join channels:",
            reply_markup=channel_manager_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data == "admin_messages":
        await query.edit_message_text(
            "📝 **Message Editor**\n\nSelect a message to edit:",
            reply_markup=message_editor_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data == "admin_settings":
        await query.edit_message_text(
            "⚙️ **Settings**\n\nConfigure bot settings:",
            reply_markup=settings_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data == "admin_stats":
        stats = get_stats()
        text = f"""📊 **Detailed Statistics**

👥 **Total Users:** {stats['users']}
📹 **Total Videos:** {stats['videos']}
🔒 **Force Join Channels:** {stats['force_join']}

🤖 **Bot Status:** ✅ Running
💾 **Database:** ✅ Connected"""
        
        await query.answer(text, show_alert=True)
    
    elif data == "admin_refresh":
        await query.answer("🔄 Refreshed!")
        await button_callback(update, context)  # Refresh current view
    
    elif data == "admin_close":
        await query.message.delete()
        await query.answer("Panel closed")
    
    elif data == "add_channel":
        admin_states[user_id] = {'action': 'add_channel'}
        await query.message.reply_text(
            "➕ **Add New Force Join Channel**\n\n"
            "Send channel details in this format:\n"
            "`channel_id username`\n\n"
            "**Example:**\n"
            "`-1001234567890 MyChannel`\n\n"
            "Or /cancel to cancel",
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data.startswith("remove_channel_"):
        channel_id = int(data.replace("remove_channel_", ""))
        if remove_force_join_channel(channel_id):
            await query.answer("✅ Channel removed!")
            await button_callback(update, context)  # Refresh list
        else:
            await query.answer("❌ Failed to remove channel", show_alert=True)
    
    elif data.startswith("edit_msg_"):
        msg_key = data.replace("edit_msg_", "")
        admin_states[user_id] = {'action': 'edit_message', 'key': msg_key}
        
        current_msg = get_message(msg_key)
        await query.message.reply_text(
            f"✏️ **Editing {msg_key.replace('_', ' ').title()}**\n\n"
            f"Current message:\n\n{current_msg}\n\n"
            f"Send the new message text or /cancel to cancel",
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data.startswith("setting_"):
        setting_key = data.replace("setting_", "")
        admin_states[user_id] = {'action': 'edit_setting', 'key': setting_key}
        
        current = get_setting(setting_key)
        await query.message.reply_text(
            f"⚙️ **Editing {setting_key.replace('_', ' ').title()}**\n\n"
            f"Current value: `{current}`\n\n"
            f"Send the new value or /cancel to cancel",
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data == "setting_protection":
        current = get_setting('video_protection', True)
        new_val = not current
        set_setting('video_protection', new_val)
        
        status = "🔒 ON" if new_val else "🔓 OFF"
        await query.answer(f"Video Protection: {status}")
        await button_callback(update, context)

# ===================== CHANNEL POST HANDLER =====================
async def channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle videos posted in channels"""
    message = update.channel_post
    
    if not message or not (message.video or message.document or message.animation):
        return
    
    channel_id = message.chat.id
    message_id = message.message_id
    channel_name = message.chat.title or "Unknown"
    
    # Save to database
    save_video(channel_id, message_id, channel_name)
    
    # Get bot username for deep link
    bot_info = await context.bot.get_me()
    bot_username = bot_info.username
    
    # Create admin notification
    deep_link = f"https://t.me/{bot_username}?start={message_id}"
    
    info_text = f"""🎬 **New Video Uploaded!**

📺 **Channel:** {channel_name}
📋 **Message ID:** `{message_id}`

🔗 **Deep Link for Mini App:**
`{message_id}`

🌐 **Direct Link:**
{deep_link}

✅ Video saved to database!
Users can now watch this video!"""
    
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=info_text,
            parse_mode=ParseMode.MARKDOWN
        )
        logger.info(f"✅ Notified admin about video {message_id} from {channel_name}")
    except Exception as e:
        logger.error(f"Error notifying admin: {e}")

# ===================== ADMIN MESSAGE HANDLER =====================
async def admin_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin text messages for editing"""
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        return
    
    if user_id not in admin_states:
        return
    
    text = update.message.text
    state = admin_states[user_id]
    
    if text == "/cancel":
        del admin_states[user_id]
        await update.message.reply_text("❌ Cancelled")
        return
    
    if state['action'] == 'add_channel':
        parts = text.split()
        if len(parts) != 2:
            await update.message.reply_text(
                "❌ Invalid format!\n\nUse: `channel_id username`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        try:
            channel_id = int(parts[0])
            username = parts[1].replace('@', '')
            
            if add_force_join_channel(channel_id, username):
                await update.message.reply_text(f"✅ Channel @{username} added!")
                del admin_states[user_id]
            else:
                await update.message.reply_text("❌ Failed to add channel")
        except ValueError:
            await update.message.reply_text("❌ Channel ID must be a number")
    
    elif state['action'] == 'edit_message':
        msg_key = state['key']
        if set_message(msg_key, text):
            await update.message.reply_text("✅ Message updated!")
            del admin_states[user_id]
        else:
            await update.message.reply_text("❌ Failed to update message")
    
    elif state['action'] == 'edit_setting':
        setting_key = state['key']
        
        # Type conversion
        if setting_key in ['main_channel_id']:
            try:
                text = int(text)
            except ValueError:
                await update.message.reply_text("❌ Must be a number")
                return
        elif setting_key in ['video_protection']:
            text = text.lower() in ['true', 'yes', '1', 'on']
        
        if set_setting(setting_key, text):
            await update.message.reply_text(f"✅ {setting_key} updated!")
            del admin_states[user_id]
        else:
            await update.message.reply_text("❌ Failed to update setting")

# ===================== ADMIN COMMANDS =====================
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin panel"""
    if update.effective_user.id != ADMIN_ID:
        return
    
    stats = get_stats()
    text = f"""🔧 **CINEFLIX ADMIN PANEL**

📊 **Statistics:**
👥 Users: {stats['users']}
📹 Videos: {stats['videos']}
🔒 Force Join: {stats['force_join']}

Select an option below:"""
    
    await update.message.reply_text(
        text,
        reply_markup=admin_main_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help"""
    await update.message.reply_text(
        get_message('help'),
        parse_mode=ParseMode.MARKDOWN
    )

# ===================== ERROR HANDLER =====================
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors"""
    logger.error(f"Update {update} caused error {context.error}")

# ===================== MAIN FUNCTION =====================
def main():
    """Start the bot"""
    logger.info("🚀 Starting CINEFLIX Ultimate Bot...")
    
    # Initialize defaults
    initialize_defaults()
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_message_handler))
    
    # Channel post handler
    application.add_handler(MessageHandler(
        filters.ChatType.CHANNEL & (filters.VIDEO | filters.Document.ALL | filters.ANIMATION),
        channel_post
    ))
    
    # Error handler
    application.add_error_handler(error_handler)
    
    logger.info("✅ CINEFLIX Ultimate Bot is running!")
    logger.info(f"👑 Admin: {ADMIN_ID}")
    logger.info(f"💾 MongoDB: Connected")
    logger.info(f"🎬 Ready to serve!")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
