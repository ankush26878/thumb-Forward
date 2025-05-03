# plugins/thumbnail.py
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database import db
from .test import get_configs, update_configs

async def handle_thumbnail_settings(bot, query):
    user_id = query.from_user.id
    data = await get_configs(user_id)
    
    # Main Thumbnail Menu
    buttons = [
        [
            InlineKeyboardButton("🖼️ Custom Thumbnail", callback_data="thumbnail#custom"),
            InlineKeyboardButton("🔘 Default Thumbnail", callback_data="thumbnail#default")
        ],
        [
            InlineKeyboardButton("💧 Watermark Settings", callback_data="thumbnail#watermark")
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="settings#main")
        ]
    ]
    
    # Current status display
    status_text = ""
    if data.get('default_thumbnail'):
        status_text += "\n\n🔘 Default Thumbnail: **ENABLED** (Removing all incoming thumbnails)"
    else:
        status_text += "\n\n🔘 Default Thumbnail: **DISABLED**"
    
    if data.get('thumbnail'):
        status_text += "\n🖼️ Custom Thumbnail: **SET**"
    else:
        status_text += "\n🖼️ Custom Thumbnail: **NOT SET**"
        
    if data.get('watermark'):
        status_text += "\n💧 Watermark: **ACTIVE**"
    else:
        status_text += "\n💧 Watermark: **INACTIVE**"
    
    await query.message.edit_text(
        f"<b>📁 Thumbnail Settings</b>\n\nConfigure how thumbnails are handled for forwarded media{status_text}",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def handle_custom_thumbnail(bot, query):
    user_id = query.from_user.id
    buttons = [
        [InlineKeyboardButton("✚ Add Thumbnail", callback_data="thumbnail#add_custom")],
        [InlineKeyboardButton("👀 View Thumbnail", callback_data="thumbnail#view_custom")],
        [InlineKeyboardButton("🗑 Remove Thumbnail", callback_data="thumbnail#remove_custom")],
        [InlineKeyboardButton("🔙 Back", callback_data="thumbnail#main")]
    ]
    
    await query.message.edit_text(
        "<b>🖼️ Custom Thumbnail Settings</b>\n\nAdd your own thumbnail that will be applied to videos and documents",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def handle_default_thumbnail(bot, query):
    user_id = query.from_user.id
    data = await get_configs(user_id)
    current_status = data.get('default_thumbnail', False)
    
    buttons = [
        [
            InlineKeyboardButton("✅ ENABLE", callback_data="thumbnail#enable_default"),
            InlineKeyboardButton("❌ DISABLE", callback_data="thumbnail#disable_default")
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="thumbnail#main")]
    ]
    
    status = "ENABLED" if current_status else "DISABLED"
    
    await query.message.edit_text(
        f"<b>🔘 Default Thumbnail Settings</b>\n\nCurrent Status: {status}\n\nWhen enabled, all incoming thumbnails will be removed and videos/documents will use their default thumbnail",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def handle_watermark_settings(bot, query):
    user_id = query.from_user.id
    buttons = [
        [InlineKeyboardButton("✚ Add Watermark", callback_data="thumbnail#add_watermark")],
        [InlineKeyboardButton("👀 View Watermark", callback_data="thumbnail#view_watermark")],
        [InlineKeyboardButton("🗑 Remove Watermark", callback_data="thumbnail#remove_watermark")],
        [InlineKeyboardButton("🔙 Back", callback_data="thumbnail#main")]
    ]
    
    await query.message.edit_text(
        "<b>💧 Watermark Settings</b>\n\nAdd a watermark that will be applied to photos and videos",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@Client.on_callback_query(filters.regex(r'^thumbnail#'))
async def thumbnail_callback_handler(bot, query):
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
        await query.answer("Default thumbnail mode enabled!")
        await handle_default_thumbnail(bot, query)
    elif action == "disable_default":
        await update_configs(query.from_user.id, 'default_thumbnail', False)
        await query.answer("Default thumbnail mode disabled!")
        await handle_default_thumbnail(bot, query)
    elif action == "add_custom":
        await query.message.delete()
        msg = await bot.ask(
            query.message.chat.id,
            "🖼️ Please send your custom thumbnail (as photo)\n\n/cancel to abort",
            filters=filters.photo | filters.text
        )
        if msg.text and msg.text.lower() == "/cancel":
            return await msg.reply("Thumbnail addition cancelled!")
        await update_configs(query.from_user.id, 'thumbnail', msg.photo.file_id)
        await msg.reply("✅ Custom thumbnail saved successfully!")
    elif action == "view_custom":
        data = await get_configs(query.from_user.id)
        if data.get('thumbnail'):
            await query.message.delete()
            await bot.send_photo(
                query.message.chat.id,
                data['thumbnail'],
                caption="Your current custom thumbnail",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="thumbnail#custom")]
                ])
            )
        else:
            await query.answer("You haven't set a custom thumbnail yet!", show_alert=True)
    elif action == "remove_custom":
        await update_configs(query.from_user.id, 'thumbnail', None)
        await query.answer("Custom thumbnail removed!")
        await handle_custom_thumbnail(bot, query)
    elif action in ["add_watermark", "view_watermark", "remove_watermark"]:
        # Similar implementation as thumbnail but for watermark
        await handle_watermark_action(bot, query, action)

async def process_media_thumbnail(file_type, file_data, user_id):
    """Process media according to thumbnail settings"""
    config = await get_configs(user_id)
    
    # 1. Handle default thumbnail (remove existing)
    if config.get('default_thumbnail'):
        if file_type in ['video', 'document']:
            file_data['thumb'] = None  # Remove thumbnail
    
    # 2. Apply custom thumbnail if set
    if config.get('thumbnail') and not config.get('default_thumbnail'):
        if file_type in ['video', 'document']:
            file_data['thumb'] = config['thumbnail']
    
    return file_data
