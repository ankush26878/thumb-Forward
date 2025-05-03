# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

import os
import asyncio
import logging
from typing import Optional, Union

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from pyrogram.errors import MessageNotModified

from database import db
from .test import get_configs, update_configs

# Configure logging
logger = logging.getLogger(__name__)

# Thumbnail Configuration Management
class ThumbnailManager:
    @staticmethod
    async def get_user_thumbnail_config(user_id: int) -> dict:
        """
        Retrieve user's thumbnail configuration
        
        :param user_id: Telegram user ID
        :return: Dictionary of thumbnail settings
        """
        try:
            user_config = await get_configs(user_id)
            return {
                'thumbnail': user_config.get('thumbnail'),
                'default_thumbnail': user_config.get('default_thumbnail', False),
                'watermark': user_config.get('watermark', False),
                'remove_thumbnails': user_config.get('remove_thumbnails', False)
            }
        except Exception as e:
            logger.error(f"Error retrieving thumbnail config for user {user_id}: {e}")
            return {}
    
    @staticmethod
    async def set_user_thumbnail(user_id: int, thumbnail_path: Optional[str] = None) -> bool:
        """Set or remove user's thumbnail
        
        :param user_id: Telegram user ID
        :param thumbnail_path: Path to thumbnail image or None to remove
        :return: Success status
        """
        try:
            await update_configs(user_id, 'thumbnail', thumbnail_path)
            return True
        except Exception as e:
            logger.error(f"Error setting thumbnail for user {user_id}: {e}")
            return False

    @staticmethod
    async def set_thumbnail_removal_preference(user_id: int, remove_thumbnails: bool) -> bool:
        """Set user's preference for thumbnail removal
        
        :param user_id: Telegram user ID
        :param remove_thumbnails: Whether to remove thumbnails during forwarding
        :return: Success status
        """
        try:
            await update_configs(user_id, 'remove_thumbnails', remove_thumbnails)
            return True
        except Exception as e:
            logger.error(f"Error setting thumbnail removal preference for user {user_id}: {e}")
            return False

async def handle_thumbnail_settings(bot: Client, query: Union[Message, CallbackQuery], action: str = None):
    try:
        # Determine user ID
        user_id = query.from_user.id if hasattr(query, 'from_user') else query.chat.id
        
        # Get current user thumbnail configuration
        user_config = await ThumbnailManager.get_user_thumbnail_config(user_id)
        
        # Thumbnail upload handler
        if action == 'upload':
            await query.message.edit_text(
                "🖼️ Please send an image to set as your default thumbnail. "
                "Send a photo within the next 5 minutes."
            )
            
            try:
                thumbnail_msg = await bot.wait_for_message(
                    chat_id=user_id, 
                    filters=filters.photo, 
                    timeout=300
                )
                
                if thumbnail_msg and thumbnail_msg.photo:
                    # Download thumbnail
                    thumbnail_path = await bot.download_media(thumbnail_msg.photo)
                    
                    # Save thumbnail to user's configuration
                    await db.update_thumbnail(user_id, thumbnail_path)
                    
                    await query.message.edit_text(
                        "✅ Thumbnail successfully uploaded and set!",
                        reply_markup=await thumbnail_buttons(user_id)
                    )
                else:
                    await query.message.edit_text(
                        "❌ Invalid thumbnail. Please send a photo.",
                        reply_markup=await thumbnail_buttons(user_id)
                    )
            
            except asyncio.TimeoutError:
                await query.message.edit_text(
                    "⏰ Thumbnail upload timed out. Please try again.",
                    reply_markup=await thumbnail_buttons(user_id)
                )
        
        # Thumbnail deletion handler
        elif action == 'delete':
            # Remove user's thumbnail
            await db.update_thumbnail(user_id, None)
            await query.message.edit_text(
                "🗑️ Your custom thumbnail has been deleted.",
                reply_markup=await thumbnail_buttons(user_id)
            )
        
        # Thumbnail export handler
        elif action == 'export':
            user_config = await db.get_user_config(user_id)
            thumbnail_path = user_config.get('thumbnail')
            
            if thumbnail_path and os.path.exists(thumbnail_path):
                await bot.send_document(
                    chat_id=user_id,
                    document=thumbnail_path,
                    caption="🖼️ Your current thumbnail"
                )
            else:
                await query.message.edit_text(
                    "❌ No thumbnail found to export.",
                    reply_markup=await thumbnail_buttons(user_id)
                )
        
        # Thumbnail import handler
        elif action == 'import':
            await query.message.edit_text(
                "📤 Please send the thumbnail image file you want to import."
            )
            
            try:
                import_msg = await bot.wait_for_message(
                    chat_id=user_id, 
                    filters=filters.document | filters.photo, 
                    timeout=300
                )
                
                if import_msg.photo or (import_msg.document and import_msg.document.mime_type.startswith('image/')):
                    # Download imported thumbnail
                    imported_thumbnail_path = await bot.download_media(import_msg)
                    
                    # Save imported thumbnail
                    await db.update_thumbnail(user_id, imported_thumbnail_path)
                    
                    await query.message.edit_text(
                        "✅ Thumbnail successfully imported!",
                        reply_markup=await thumbnail_buttons(user_id)
                    )
                else:
                    await query.message.edit_text(
                        "❌ Invalid file. Please send an image.",
                        reply_markup=await thumbnail_buttons(user_id)
                    )
            
            except asyncio.TimeoutError:
                await query.message.edit_text(
                    "⏰ Thumbnail import timed out. Please try again.",
                    reply_markup=await thumbnail_buttons(user_id)
                )
        
        # Default settings view
        else:
            user_config = await db.get_user_config(user_id)
            thumbnail_status = "No custom thumbnail set" if not user_config.get('thumbnail') else "Custom thumbnail is set"
            
            await query.message.edit_text(
                f"**🖼️ Thumbnail Settings**\n\n{thumbnail_status}\n\nManage your thumbnail preferences here.",
                reply_markup=await thumbnail_buttons(user_id)
            )
    
    except Exception as e:
        logger.error(f"Thumbnail settings error: {e}")
        await query.message.edit_text(
            f"❌ An error occurred: {str(e)}",
            reply_markup=await thumbnail_buttons(user_id)
        )

async def handle_custom_thumbnail(bot, query):
    user_id = query.from_user.id
    buttons = await thumbnail_buttons(user_id)
    await query.message.edit_text(
        "**🖼️ Custom Thumbnail Settings**\n\nManage your custom thumbnail here.",
        reply_markup=buttons
    )

async def handle_default_thumbnail(bot, query):
    """Handle default thumbnail settings menu"""
    try:
        await query.message.edit_text(
            "**🔘 Default Thumbnail Settings**\n\n"
            "Enable or disable the default thumbnail feature.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Eɴᴀʙʟᴇ Dᴇғᴀᴜʟᴛ Tʜᴜᴍʙɴᴀɪʟ", callback_data="thumbnail#enable_default")],
                [InlineKeyboardButton("❌ Dɪsᴀʙʟᴇ Dᴇғᴀᴜʟᴛ Tʜᴜᴍʙɴᴀɪʟ", callback_data="thumbnail#disable_default")],
                [InlineKeyboardButton("⫷ Bᴀᴄᴋ", callback_data="thumbnail#main")]
            ])
        )
    except Exception as e:
        logger.error(f"Error in handle_default_thumbnail: {e}")
        await query.answer("An error occurred. Please try again.")

async def handle_default_thumbnail_action(bot, query, enable: bool):
    user_id = query.from_user.id
    
    try:
        await update_configs(user_id, 'default_thumbnail', enable)
        status = "enabled" if enable else "disabled"
        await query.answer(f"Default thumbnail {status}!")
        await handle_default_thumbnail(bot, query)
    except Exception as e:
        await query.answer("⚠️ Failed to update default thumbnail setting.", show_alert=True)
        print(f"Error in handle_default_thumbnail_action: {e}")

async def handle_thumbnail_removal_toggle(bot, query):
    user_id = query.from_user.id
    
    try:
        user_config = await ThumbnailManager.get_user_thumbnail_config(user_id)
        current_status = user_config.get('remove_thumbnails', False)
        new_status = not current_status
        
        await ThumbnailManager.set_thumbnail_removal_preference(user_id, new_status)
        
        status_text = "enabled" if new_status else "disabled"
        await query.answer(f"Thumbnail removal {status_text}!")
        
        # Update the message with new buttons showing updated status
        await query.message.edit_text(
            "**🖼️ Thumbnail Settings**\n\nManage your thumbnail preferences here.",
            reply_markup=await thumbnail_buttons(user_id)
        )
    except Exception as e:
        logger.error(f"Error toggling thumbnail removal: {e}", exc_info=True)
        await query.answer("⚠️ Failed to update thumbnail removal setting.", show_alert=True)

async def handle_watermark_settings(bot, query):
    """Handle watermark settings menu"""
    try:
        await query.message.edit_text(
            "**💧 Wᴀᴛᴇʀᴍᴀʀᴋ Sᴇᴛᴛɪɴɢs**\n\n"
            "Manage your watermark preferences here.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✚ Aᴅᴅ Wᴀᴛᴇʀᴍᴀʀᴋ", callback_data="thumbnail#add_watermark")],
                [InlineKeyboardButton("👀 Vɪᴇᴡ Wᴀᴛᴇʀᴍᴀʀᴋ", callback_data="thumbnail#view_watermark")],
                [InlineKeyboardButton("🗑 Rᴇᴍᴏᴠᴇ Wᴀᴛᴇʀᴍᴀʀᴋ", callback_data="thumbnail#remove_watermark")],
                [InlineKeyboardButton("⫷ Bᴀᴄᴋ", callback_data="thumbnail#main")]
            ])
        )
    except Exception as e:
        logger.error(f"Error in handle_watermark_settings: {e}")
        await query.answer("An error occurred. Please try again.")

async def handle_watermark_action(bot, query, action):
    user_id = query.from_user.id

    try:
        data = await get_configs(user_id)
    except Exception as e:
        await query.answer("⚠️ Error fetching watermark settings.", show_alert=True)
        print(f"Error in handle_watermark_action: {e}")
        return

    if action == "add_watermark":
        await query.message.delete()
        msg = await bot.ask(
            query.message.chat.id,
            "💧 Please send your watermark image (as photo)\n\n/cancel to abort",
            filters=filters.photo | filters.text,
            timeout=300
        )
        if msg.text and msg.text.lower() == "/cancel":
            return await msg.reply("❌ Watermark addition cancelled!")
        if not msg.photo:
            return await msg.reply("⚠️ That is not a photo. Please try again.")
        try:
            await update_configs(user_id, 'watermark', msg.photo.file_id)
            await msg.reply("✅ Watermark saved successfully!")
        except Exception as e:
            await msg.reply("⚠️ Failed to save watermark.")
            print(f"Error saving watermark: {e}")

    elif action == "view_watermark":
        if data.get('watermark'):
            await query.message.delete()
            try:
                await bot.send_photo(
                    query.message.chat.id,
                    data['watermark'],
                    caption="Your current watermark image",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⫷ Bᴀᴄᴋ", callback_data="thumbnail#watermark")]
                    ])
                )
            except Exception as e:
                await query.answer("⚠️ Unable to send watermark photo.", show_alert=True)
                print(f"Error sending watermark photo: {e}")
        else:
            await query.answer("❌ You haven't set a watermark yet!", show_alert=True)

    elif action == "remove_watermark":
        try:
            await update_configs(user_id, 'watermark', None)
            await query.answer("🗑 Watermark removed!")
            await handle_watermark_settings(bot, query)
        except Exception as e:
            await query.answer("⚠️ Failed to remove watermark.", show_alert=True)
            print(f"Error removing watermark: {e}")

@Client.on_callback_query(filters.regex(r'^thumbnail#'))
async def thumbnail_callback_handler(bot: Client, query: CallbackQuery):
    try:
        user_id = query.from_user.id
        data = query.data.split("#")
        action = data[1] if len(data) > 1 else None
        
        if action == "custom":
            await handle_custom_thumbnail(bot, query)
        elif action == "add_custom":
            await handle_add_custom_thumbnail(bot, query)
        elif action == "view_custom":
            await handle_view_custom_thumbnail(bot, query)
        elif action == "remove_custom":
            await handle_remove_custom_thumbnail(bot, query)
        elif action == "default":
            await handle_default_thumbnail(bot, query)
        elif action == "watermark":
            await handle_watermark_settings(bot, query)
        elif action == "enable_default":
            await handle_default_thumbnail_action(bot, query, True)
        elif action == "disable_default":
            await handle_default_thumbnail_action(bot, query, False)
            msg = await bot.ask(
                query.message.chat.id,
                "🖼️ Please send your custom thumbnail (as photo)\n\n/cancel to abort",
                filters=filters.photo | filters.text,
                timeout=300
            )
            if msg.text and msg.text.lower() == "/cancel":
                return await msg.reply("❌ Thumbnail addition cancelled!")
            if not msg.photo:
                return await msg.reply("⚠️ That is not a photo. Please try again.")
            try:
                await update_configs(query.from_user.id, 'thumbnail', msg.photo.file_id)
                await msg.reply("✅ Custom thumbnail saved successfully!")
            except Exception as e:
                await msg.reply("⚠️ Failed to save custom thumbnail.")
                print(f"Error saving custom thumbnail: {e}")
        elif action == "view_custom":
            data = await get_configs(query.from_user.id)
            if data.get('thumbnail'):
                await query.message.delete()
                try:
                    await bot.send_photo(
                        query.message.chat.id,
                        data['thumbnail'],
                        caption="Your current custom thumbnail",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🔙 Bᴀᴄᴋ", callback_data="thumbnail#custom")]
                        ])
                    )
                except Exception as e:
                    await query.answer("⚠️ Unable to send custom thumbnail photo.", show_alert=True)
                    print(f"Error sending custom thumbnail photo: {e}")
            else:
                await query.answer("❌ You haven't set a custom thumbnail yet!", show_alert=True)
        elif action == "remove_custom":
            try:
                await update_configs(query.from_user.id, 'thumbnail', None)
                await query.answer("🗑 Custom thumbnail removed!")
                await handle_custom_thumbnail(bot, query)
            except Exception as e:
                await query.answer("⚠️ Failed to remove custom thumbnail.", show_alert=True)
                print(f"Error removing custom thumbnail: {e}")
        elif action in ["add_watermark", "view_watermark", "remove_watermark"]:
            await handle_watermark_action(bot, query, action)
        elif action == "toggle_removal":
            await handle_thumbnail_removal_toggle(bot, query)
        else:
            await query.answer("❓ Unknown action.", show_alert=True)
    except Exception as e:
        await query.answer("⚠️ An error occurred. Please try again later.", show_alert=True)
        print(f"Unexpected error in thumbnail_callback_handler: {e}")

async def process_media_thumbnail(file_type: str, file_data: dict, user_id: int) -> dict:
    try:
        # Check user-specific thumbnail removal settings
        user_config = await ThumbnailManager.get_user_thumbnail_config(user_id)
        
        # Only remove thumbnail if user has enabled this setting
        if user_config.get('remove_thumbnails', False):
            file_data['thumbnail'] = None
            logger.info(f'Removed thumbnail for {file_type} during forwarding')
        
        return file_data
    
    except Exception as e:
        logger.error(f'Thumbnail processing error: {e}')
        return file_data

async def thumbnail_buttons(user_id=None):
    logger.info(f"Generating thumbnail buttons for user_id: {user_id}")
    try:
        if user_id:
            user_config = await get_configs(user_id)
            remove_status = "✅ Enabled" if user_config.get('remove_thumbnails', False) else "❌ Disabled"
            logger.info(f"User {user_id} thumbnail removal status: {remove_status}")
        else:
            remove_status = "❌ Disabled"
            logger.info("No user_id provided, defaulting to disabled")
        
        buttons = [
            [InlineKeyboardButton("✚ Aᴅᴅ Tʜᴜᴍʙɴᴀɪʟ", callback_data="thumbnail#custom")],
            [InlineKeyboardButton("👀 Vɪᴇᴡ Tʜᴜᴍʙɴᴀɪʟ", callback_data="thumbnail#view_custom")],
            [InlineKeyboardButton("🗑 Rᴇᴍᴏᴠᴇ Tʜᴜᴍʙɴᴀɪʟ", callback_data="thumbnail#remove_custom")],
            [InlineKeyboardButton("🔘 Dᴇғᴀᴜʟᴛ Tʜᴜᴍʙɴᴀɪʟ", callback_data="thumbnail#default")],
            [InlineKeyboardButton(f"🔄 Aᴜᴛᴏ-Rᴇᴍᴏᴠᴇ Tʜᴜᴍʙɴᴀɪʟs: {remove_status}", callback_data="thumbnail#toggle_removal")],
            [InlineKeyboardButton("💧 Wᴀᴛᴇʀᴍᴀʀᴋ Sᴇᴛᴛɪɴɢs", callback_data="thumbnail#watermark")],
            [InlineKeyboardButton("⫷ Bᴀᴄᴋ", callback_data="settings#main")]
        ]
        logger.info(f"Generated thumbnail buttons: {buttons}")
        return InlineKeyboardMarkup(buttons)
    except Exception as e:
        logger.error(f"Error generating thumbnail buttons: {e}", exc_info=True)
        # Fallback buttons
        buttons = [
            [InlineKeyboardButton("✚ Aᴅᴅ Tʜᴜᴍʙɴᴀɪʟ", callback_data="thumbnail#custom")],
            [InlineKeyboardButton("⫷ Bᴀᴄᴋ", callback_data="settings#main")]
        ]
        return InlineKeyboardMarkup(buttons)
