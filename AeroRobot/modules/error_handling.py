"""
MIT License
Copyright (C) 2017-2019, Paul Larsen
Copyright (C) 2022 Hodacka
Copyright (c) 2022, Yūki • Black Knights Union, <https://github.com/AerodynamicV1Botz/Aero-Robot>
This file is part of @Aero_Management_Bot (Telegram Bot)
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the Software), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED AS IS, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import traceback

import requests
import html
import random
import sys
import pretty_errors
import io
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext, CommandHandler
from AeroRobot import dispatcher, DEV_USERS, OWNER_ID

pretty_errors.mono()


class ErrorsDict(dict):
    "A custom dict to store errors and their count"

    def __init__(self, *args, **kwargs):
        self.raw = []
        super().__init__(*args, **kwargs)

    def __contains__(self, error):
        self.raw.append(error)
        error.identifier = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=5))
        for e in self:
            if type(e) is type(error) and e.args == error.args:
                self[e] += 1
                return True
        self[error] = 0
        return False

    def __len__(self):
        return len(self.raw)


errors = ErrorsDict()


def error_callback(update: Update, context: CallbackContext):
    if not update:
        return
    if context.error in errors:
        return
    try:
        stringio = io.StringIO()
        pretty_errors.output_stderr = stringio
        output = pretty_errors.excepthook(
            type(context.error), context.error, context.error.__traceback__,
        )
        pretty_errors.output_stderr = sys.stderr
        pretty_error = stringio.getvalue()
        stringio.close()
    except:
        pretty_error = "Failed to create pretty error."
    tb_list = traceback.format_exception(
        None, context.error, context.error.__traceback__,
    )
    tb = "".join(tb_list)
    pretty_message = (
        "{}\n"
        "-------------------------------------------------------------------------------\n"
        "An exception was raised while handling an update\n"
        "User: {}\n"
        "Chat: {} {}\n"
        "Callback data: {}\n"
        "Message: {}\n\n"
        "Full Traceback: {}"
    ).format(
            pretty_error,
        update.effective_user.id,
        update.effective_chat.title if update.effective_chat else "",
        update.effective_chat.id if update.effective_chat else "",
        update.callback_query.data if update.callback_query else "None",
        update.effective_message.text if update.effective_message else "No message",
        tb,
    )
    key = requests.post(
        "https://aerodynamicbin.com/api/documents", json={"content": pretty_message},
    ).json()
    e = html.escape(f"{context.error}")
    if not key.get("result", {}).get("key"):
        with open("error.txt", "w+") as f:
            f.write(pretty_message)
        context.bot.send_document(
            OWNER_ID,
                open("error.txt", "rb"),
                caption=f"#{context.error.identifier}\n<b>An unknown error occured:</b>\n<code>{e}</code>",
                parse_mode="html",
        )
        return
    key = key.get("result").get("key")
    url = f"https://aerodynamicbin.com/{key}.py"
    context.bot.send_message(
        OWNER_ID,
            text=f"#{context.error.identifier}\n<b>An unknown error occured:</b>\n<code>{e}</code>",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Aerodynamicbin", url=url)]],
            ),
        parse_mode="html",
    )


def list_errors(update: Update, context: CallbackContext):
    if update.effective_user.id not in DEV_USERS:
        return
    e = {
        k: v for k, v in sorted(errors.items(), key=lambda item: item[1], reverse=True)
    }
    msg = "<b>Errors List:</b>\n"
    for x in e:
        msg += f"• <code>{x}:</code> <b>{e[x]}</b> #{x.identifier}\n"
    msg += f"{len(errors)} have occurred since startup."
    if len(msg) > 4096:
        with open("errors_msg.txt", "w+") as f:
            f.write(msg)
        context.bot.send_document(
            update.effective_chat.id,
            open("errors_msg.txt", "rb"),
            caption=f"Too many errors have occured..",
            parse_mode="html",
        )
        return
    update.effective_message.reply_text(msg, parse_mode="html")


dispatcher.add_error_handler(error_callback)
dispatcher.add_handler(CommandHandler("errors", list_errors))
