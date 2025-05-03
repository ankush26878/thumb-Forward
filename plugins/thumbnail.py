from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database import db
from .test import get_configs, update_configs
import os
import logging
import asyncio
from typing import Optional, Union

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
                'watermark': user_config.get('watermark', False)
            }
        except Exception as e:
            logger.error(f"Error retrieving thumbnail config for user {user_id}: {e}")
            return {}
    
    @staticmethod
    async def set_user_thumbnail(user_id: int, thumbnail_path: Optional[str] = None) -> bool:
        """
        Set or remove user's thumbnail
        
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
                        reply_markup=thumbnail_buttons(user_id)
                    )
                else:
                    await query.message.edit_text(
                        "❌ Invalid thumbnail. Please send a photo.",
                        reply_markup=thumbnail_buttons(user_id)
                    )
            
            except asyncio.TimeoutError:
                await query.message.edit_text(
                    "⏰ Thumbnail upload timed out. Please try again.",
                    reply_markup=thumbnail_buttons(user_id)
                )
        
        # Thumbnail deletion handler
        elif action == 'delete':
            # Remove user's thumbnail
            await db.update_thumbnail(user_id, None)
            await query.message.edit_text(
                "🗑️ Your custom thumbnail has been deleted.",
                reply_markup=thumbnail_buttons(user_id)
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
                    reply_markup=thumbnail_buttons(user_id)
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
                        reply_markup=thumbnail_buttons(user_id)
                    )
                else:
                    await query.message.edit_text(
                        "❌ Invalid file. Please send an image.",
                        reply_markup=thumbnail_buttons(user_id)
                    )
            
            except asyncio.TimeoutError:
                await query.message.edit_text(
                    "⏰ Thumbnail import timed out. Please try again.",
                    reply_markup=thumbnail_buttons(user_id)
                )
        
        # Default settings view
        else:
            user_config = await db.get_user_config(user_id)
            thumbnail_status = "No custom thumbnail set" if not user_config.get('thumbnail') else "Custom thumbnail is set"
            
            await query.message.edit_text(
                f"**🖼️ Thumbnail Settings**\n\n{thumbnail_status}\n\nManage your thumbnail preferences here.",
                reply_markup=thumbnail_buttons(user_id)
            )
    
    except Exception as e:
        logger.error(f"Thumbnail settings error: {e}")
        await query.message.edit_text(
            f"❌ An error occurred: {str(e)}",
            reply_markup=thumbnail_buttons(user_id)
        )

async def handle_custom_thumbnail(bot, query):
    buttons = [
        [InlineKeyboardButton("✚ Add Thumbnail", callback_data="thumbnail#add_custom")],
        [InlineKeyboardButton("👀 View Thumbnail", callback_data="thumbnail#view_custom")],
        [InlineKeyboardButton("🗑 Remove Thumbnail", callback_data="thumbnail#remove_custom")],
        [InlineKeyboardButton("🔙 Back", callback_data="thumbnail#main")]
    ]
    
    try:
        await query.message.edit_text(
            "<b>🖼️ Custom Thumbnail Settings</b>\n\nAdd your own thumbnail that will be applied to videos and documents",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except Exception as e:
        await query.answer("⚠️ Unable to update message.", show_alert=True)
        print(f"Error editing custom thumbnail message: {e}")

async def handle_default_thumbnail(bot, query):
    user_id = query.from_user.id
    try:
        data = await get_configs(user_id)
    except Exception as e:
        await query.answer("⚠️ Error fetching default thumbnail setting.", show_alert=True)
        print(f"Error in handle_default_thumbnail: {e}")
        return
    
    current_status = data.get('default_thumbnail', False)
    
    buttons = [
        [
            InlineKeyboardButton("✅ ENABLE", callback_data="thumbnail#enable_default"),
            InlineKeyboardButton("❌ DISABLE", callback_data="thumbnail#disable_default")
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="thumbnail#main")]
    ]
    
    status = "ENABLED" if current_status else "DISABLED"
    
    try:
        await query.message.edit_text(
            f"<b>🔘 Default Thumbnail Settings</b>\n\nCurrent Status: {status}\n\nWhen enabled, all incoming thumbnails will be removed and videos/documents will use their default thumbnail",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except Exception as e:
        await query.answer("⚠️ Unable to update message.", show_alert=True)
        print(f"Error editing default thumbnail message: {e}")

async def handle_watermark_settings(bot, query):
    buttons = [
        [InlineKeyboardButton("✚ Add Watermark", callback_data="thumbnail#add_watermark")],
        [InlineKeyboardButton("👀 View Watermark", callback_data="thumbnail#view_watermark")],
        [InlineKeyboardButton("🗑 Remove Watermark", callback_data="thumbnail#remove_watermark")],
        [InlineKeyboardButton("🔙 Back", callback_data="thumbnail#main")]
    ]
    
    try:
        await query.message.edit_text(
            "<b>💧 Watermark Settings</b>\n\nAdd a watermark that will be applied to photos and videos",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except Exception as e:
        await query.answer("⚠️ Unable to update message.", show_alert=True)
        print(f"Error editing watermark settings message: {e}")

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
                    caption="Your current watermark",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Back", callback_data="thumbnail#watermark")]
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
async def thumbnail_callback_handler(bot, query):
    try:
        action = query.data.split('#')[1]
        
        if action == "main":
            await handle_thumbnail_settings(bot, query)
        elif action == "custom":
            await handle_custom_thumbnail(bot, query)
        elif action == "default":
            await handle_default_thumbnail(bot, query)
        elif action == "watermark":
            await handle_watermark_settings(bot, query)
        elif action == "enable_default":
            await update_configs(query.from_user.id, 'default_thumbnail', True)
            await query.answer("✅ Default thumbnail mode enabled!")
            await handle_default_thumbnail(bot, query)
        elif action == "disable_default":
            await update_configs(query.from_user.id, 'default_thumbnail', False)
            await query.answer("❌ Default thumbnail mode disabled!")
            await handle_default_thumbnail(bot, query)
        elif action == "add_custom":
            await query.message.delete()
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
                            [InlineKeyboardButton("🔙 Back", callback_data="thumbnail#custom")]
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
        else:
            await query.answer("❓ Unknown action.", show_alert=True)
    except Exception as e:
        await query.answer("⚠️ An error occurred. Please try again later.", show_alert=True)
        print(f"Unexpected error in thumbnail_callback_handler: {e}")

async def process_media_thumbnail(file_type: str, file_data: dict, user_id: int) -> dict:
    try:
        # Retrieve user's thumbnail configuration
        user_config = await ThumbnailManager.get_user_thumbnail_config(user_id)
        
        # Thumbnail management buttons
        thumbnail_buttons = [
            [InlineKeyboardButton("🖼️ Set Custom Thumbnail", callback_data="thumbnail#custom")],
            [InlineKeyboardButton("🔘 Remove Thumbnails", callback_data="thumbnail#default")]
        ]
        
        # Always remove existing thumbnails for videos and documents
        if file_type in ['video', 'document', 'photo']:
            file_data['thumbnail'] = None
            logger.info(f'Removed existing thumbnail for {file_type} for user {user_id}')
        
        # Apply custom thumbnail if explicitly set and not in default mode
        if (user_config.get('thumbnail') and 
            not user_config.get('default_thumbnail') and 
            file_type in ['video', 'document', 'photo']):
            
            file_data['thumbnail'] = user_config['thumbnail']
            logger.info(f'Applied custom thumbnail for {file_type} for user {user_id}')
        
        # Watermark processing (placeholder)
        if user_config.get('watermark') and file_type in ['photo', 'video']:
            try:
                # Implement actual watermark logic here
                logger.info(f'Watermark processing for {file_type}')
            except Exception as watermark_error:
                logger.error(f'Watermark processing error: {watermark_error}')
        
        # Add thumbnail management buttons
        file_data['thumbnail_settings_buttons'] = InlineKeyboardMarkup(thumbnail_buttons)
        
        return file_data
    
    except Exception as e:
        logger.error(f'Thumbnail processing error for user {user_id}: {e}')
        return file_data

def thumbnail_buttons(user_id=None):
    buttons = [
        [InlineKeyboardButton('📸 Upload Thumbnail', callback_data='thumbnail#upload')],
        [InlineKeyboardButton('🗑️ Delete Thumbnail', callback_data='thumbnail#delete')],
        [InlineKeyboardButton('📤 Export Thumbnail', callback_data='thumbnail#export')],
        [InlineKeyboardButton('📥 Import Thumbnail', callback_data='thumbnail#import')],
        [InlineKeyboardButton('🔙 Back to Settings', callback_data='settings#extra')]
    ]
    return InlineKeyboardMarkup(buttons)
