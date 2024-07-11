import logging
from telegram import Update, ChatPermissions
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from datetime import datetime, timedelta
import os
import sys
import json

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Define global variables
delete_time = timedelta(minutes=1)  # Default delete time for user messages
mute_time = timedelta(minutes=5)  # Default mute time
bot_message_delete_time = timedelta(seconds=120)  # Delete bot messages after 120 seconds
message_times = {}
targeted_groups_file = 'targeted_groups.json'
BOT_OWNER_ID = 622730585  # Replace with your actual bot owner ID

# Add more links to instantly AutoDelete links
delete_links = ['t.me', '@', 'http', 'www', 'https', 'https://t.me', 'telegram.dog',
                'telegram.me', 'wa.me', 'youtube.com', 'youtu.be', 'x.com',
                'facebook.com', 'instagram.com']

# Load targeted groups from file
def load_targeted_groups():
    if os.path.exists(targeted_groups_file):
        with open(targeted_groups_file, 'r') as file:
            return json.load(file)
    return []

targeted_groups = load_targeted_groups()

# Save targeted groups to file
def save_targeted_groups():
    with open(targeted_groups_file, 'w') as file:
        json.dump(targeted_groups, file)

# Function to delete messages
def delete_message(context: CallbackContext):
    chat_id, message_id = context.job.context
    context.bot.delete_message(chat_id=chat_id, message_id=message_id)

# Schedule deletion of bot messages
def schedule_bot_message_deletion(message, context: CallbackContext):
    context.job_queue.run_once(delete_message, bot_message_delete_time.total_seconds(), context=(message.chat_id, message.message_id))

# Command to set the delete time
def set_time(update: Update, context: CallbackContext) -> None:
    global delete_time
    try:
        time_str = context.args[0]
        time_value, time_unit = int(time_str[:-1]), time_str[-1]
        if time_unit == 'm':
            delete_time = timedelta(minutes=time_value)
        elif time_unit == 'h':
            delete_time = timedelta(hours=time_value)
        elif time_unit == 'd':
            delete_time = timedelta(days=time_value)
        msg = update.message.reply_text(f'Delete time set to {delete_time}.')
        schedule_bot_message_deletion(msg, context)
    except (IndexError, ValueError):
        msg = update.message.reply_text('Usage: /set_time <number><m/h/d>')
        schedule_bot_message_deletion(msg, context)

# Command to set the mute time
def set_punis(update: Update, context: CallbackContext) -> None:
    global mute_time
    try:
        time_str = context.args[0]
        time_value, time_unit = int(time_str[:-1]), time_str[-1]
        if time_unit == 'm':
            mute_time = timedelta(minutes=time_value)
        elif time_unit == 'h':
            mute_time = timedelta(hours=time_value)
        elif time_unit == 'd':
            mute_time = timedelta(days=time_value)
        msg = update.message.reply_text(f'Mute time set to {mute_time}.')
        schedule_bot_message_deletion(msg, context)
    except (IndexError, ValueError):
        msg = update.message.reply_text('Usage: /set_punis <number><m/h/d>')
        schedule_bot_message_deletion(msg, context)

# Handler to delete links and schedule message deletion
def handle_message(update: Update, context: CallbackContext) -> None:
    message = update.message
    chat_id = message.chat_id
    user_id = message.from_user.id
    message_id = message.message_id
    text = message.text

    if chat_id not in targeted_groups:
        return  # Ignore messages from non-targeted groups

    # Check for links
    if any(link in text.lower() for link in delete_links):
        message.delete()
        context.bot.restrict_chat_member(chat_id, user_id, ChatPermissions(can_send_messages=False), until_date=datetime.now() + mute_time)
        msg = context.bot.send_message(chat_id, f'{message.from_user.first_name} has been muted for {mute_time}.')
        schedule_bot_message_deletion(msg, context)
    else:
        # Schedule message deletion
        context.job_queue.run_once(delete_message, delete_time.total_seconds(), context=(chat_id, message_id))

# Command to start the bot and provide usage instructions
def start(update: Update, context: CallbackContext) -> None:
    msg = update.message.reply_text("Welcome to the AutoDelete Bot!\n\n"
                                    "Usage instructions:\n"
                                    "- Send any message containing a link to have it instantly deleted.\n"
                                    "- Use /set_time <number><m/h/d> to set the auto-delete time for messages (default is 1 minute).\n"
                                    "- Use /set_punis <number><m/h/d> to set the mute time for users sending links (default is 5 minutes).\n"
                                    "- Use /add_group <group_id> to add a targeted group.\n"
                                    "- Use /remove_group <group_id> to remove a targeted group.\n"
                                    "- Use /groups to list connected groups with their titles.")
    schedule_bot_message_deletion(msg, context)

# Command to restart the bot script (works only for the bot owner)
def restart(update: Update, context: CallbackContext) -> None:
    if update.message.from_user.id == BOT_OWNER_ID:
        update.message.reply_text("Restarting...")

        # Stop the updater
        context.bot.stop_polling()

        # Start a new updater
        new_updater = Updater(token=TOKEN, use_context=True)
        new_updater.dispatcher.add_handler(CommandHandler("start", start))
        new_updater.dispatcher.add_handler(CommandHandler("help", help_command))
        # Add other handlers here...

        new_updater.start_polling()
        new_updater.idle()
    else:
        msg = update.message.reply_text("You are not authorized to restart the bot.")
        schedule_bot_message_deletion(msg, context)

# Command to view logs (works only for the bot owner)
def logs(update: Update, context: CallbackContext) -> None:
    if update.message.from_user.id == BOT_OWNER_ID:
        with open('bot.log', 'r') as log_file:
            logs = log_file.read()

        # Split logs into chunks of 4096 characters
        for chunk in [logs[i:i + 4096] for i in range(0, len(logs), 4096)]:
            update.message.reply_text(chunk)

    else:
        msg = update.message.reply_text("You are not authorized to view logs.")
        schedule_bot_message_deletion(msg, context)

# Command to add a targeted group
def add_group(update: Update, context: CallbackContext) -> None:
    if update.message.from_user.id == BOT_OWNER_ID:
        try:
            group_id = int(context.args[0])
            if group_id not in targeted_groups:
                targeted_groups.append(group_id)
                save_targeted_groups()
                msg = update.message.reply_text(f'Group {group_id} added to targeted groups.')
                schedule_bot_message_deletion(msg, context)
            else:
                msg = update.message.reply_text(f'Group {group_id} is already a targeted group.')
                schedule_bot_message_deletion(msg, context)
        except (IndexError, ValueError):
            msg = update.message.reply_text('Usage: /add_group <group_id>')
            schedule_bot_message_deletion(msg, context)
    else:
        msg = update.message.reply_text("You are not authorized to add groups.")
        schedule_bot_message_deletion(msg, context)

# Command to remove a targeted group
def remove_group(update: Update, context: CallbackContext) -> None:
    if update.message.from_user.id == BOT_OWNER_ID:
        try:
            group_id = int(context.args[0])
            if group_id in targeted_groups:
                targeted_groups.remove(group_id)
                save_targeted_groups()
                msg = update.message.reply_text(f'Group {group_id} removed from targeted groups.')
                schedule_bot_message_deletion(msg, context)
            else:
                msg = update.message.reply_text(f'Group {group_id} is not a targeted group.')
                schedule_bot_message_deletion(msg, context)
        except (IndexError, ValueError):
            msg = update.message.reply_text('Usage: /remove_group <group_id>')
            schedule_bot_message_deletion(msg, context)
    else:
        msg = update.message.reply_text("You are not authorized to remove groups.")
        schedule_bot_message_deletion(msg, context)

# Command to list connected groups with titles
def list_groups(update: Update, context: CallbackContext) -> None:
    if update.message.from_user.id == BOT_OWNER_ID:
        msg = "Connected groups:\n"
        for group_id in targeted_groups:
            try:
                chat = context.bot.get_chat(group_id)
                title = chat.title
                msg += f"- {title} (ID: {group_id})\n"
            except Exception as e:
                logger.error(f"Error fetching group info for group ID {group_id}: {e}")
                msg += f"- Unknown group (ID: {group_id})\n"
        update.message.reply_text(msg)
    else:
        msg = update.message.reply_text("You are not authorized to list groups.")
        schedule_bot_message_deletion(msg, context)

def main():
    # Create the Updater and pass it your bot's token.
    updater = Updater("7193468978:AAFusqzvq0LfAVL34KX68YZglb8O0M9D4hk")  # Replace YOUR_BOT_TOKEN with your actual bot token

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # Register command handlers
    dispatcher.add_handler(CommandHandler("set_time", set_time))
    dispatcher.add_handler(CommandHandler("set_punis", set_punis))
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("restart", restart))
    dispatcher.add_handler(CommandHandler("logs", logs))
    dispatcher.add_handler(CommandHandler("add_group", add_group))
    dispatcher.add_handler(CommandHandler("remove_group", remove_group))
    dispatcher.add_handler(CommandHandler("groups", list_groups))

    # Register message handler
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C
    updater.idle()

if __name__ == '__main__':
    main()