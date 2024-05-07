from gpytranslate import Translator

from os import getenv
from tiktoken import encoding_for_model

from db import DataBase
from openaitools import OpenAiTools
from stablediffusion import StableDiffusion
from cryptopay import CryptoPay

from dotenv import load_dotenv
from aiofiles.os import remove

import asyncio

from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.types.input_file import FSInputFile
from aiogram import F


class States(StatesGroup):
    ENTRY_STATE = State()
    CHATGPT_STATE = State()
    DALL_E_STATE = State()
    STABLE_STATE = State()
    INFO_STATE = State()
    PURCHASE_STATE = State()
    PURCHASE_CHATGPT_STATE = State()
    PURCHASE_DALL_E_STATE = State()
    PURCHASE_STABLE_STATE = State()


dp = Dispatcher()


# Starts a conversation
@dp.message(Command('start'))
@dp.message(States.ENTRY_STATE, F.text.regexp(r'^🔙Back$'))
@dp.message(States.CHATGPT_STATE, F.text.regexp(r'^🔙Back$'))
@dp.message(States.DALL_E_STATE, F.text.regexp(r'^🔙Back$'))
@dp.message(States.STABLE_STATE, F.text.regexp(r'^🔙Back$'))
@dp.message(States.INFO_STATE, F.text.regexp(r'^🔙Back$'))
async def start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username
    result = await DataBase.is_user(user_id)

    button = [[KeyboardButton(text="💭Общение — ChatGPT")],
              [KeyboardButton(text="🌄Генерация изображений — DALL·E")],
              [KeyboardButton(text="🌅Генерация изображений — Stable Diffusion")],
              [KeyboardButton(text="👤Мой аккаунт | 💰Купить")]]
    reply_markup = ReplyKeyboardMarkup(
        keyboard=button, resize_keyboard=True
    )

    if not result:
        await DataBase.insert_user(user_id, username)
        await message.answer(
            text="👋У вас есть: \n💭3000 токенов ChatGPT \n🌄3 генераций изображений DALL·E \n🌅3 генераций STABLE DIFFUSION изображений \n Выберите вариант: 👇 \n Если кнопки не работают, введите команду /start",
            reply_markup=reply_markup,
        )
    else:
        await message.answer(
            text="Выберите вариант: 👇🏻 \n Если кнопки не работают, введите команду /start.",
            reply_markup=reply_markup,
        )
    await state.set_state(States.ENTRY_STATE)


# Question Handling
@dp.message(States.ENTRY_STATE, F.text.regexp(r'^💭Общение — ChatGPT$'))
@dp.message(States.ENTRY_STATE, F.text.regexp(r'^🌄Генерация изображений — DALL·E$'))
@dp.message(States.ENTRY_STATE, F.text.regexp(r'^🌅Генерация изображений — Stable Diffusion$'))
async def question_handler(message: types.Message, state: FSMContext):
    button = [[KeyboardButton(text="🔙Back")]]
    reply_markup = ReplyKeyboardMarkup(
        keyboard=button, resize_keyboard=True
    )
    await message.answer(
        text="Enter your text: 👇🏻",
        reply_markup=reply_markup,
    )
    option = message.text
    if option == "💭Общение — ChatGPT":
        await state.set_state(States.CHATGPT_STATE)
    elif option == "🌄Генерация изображений — DALL·E":
        await state.set_state(States.DALL_E_STATE)
    elif option == "🌅Генерация изображений — Stable Diffusion":
        await state.set_state(States.STABLE_STATE)


# Answer Handling
@dp.message(States.CHATGPT_STATE, F.text)
async def chatgpt_answer_handler(message: types.Message, state: FSMContext):
    button = [[KeyboardButton(text="🔙Назад")]]
    reply_markup = ReplyKeyboardMarkup(
        keyboard=button, resize_keyboard=True
    )

    user_id = message.from_user.id
    result = await DataBase.get_chatgpt(user_id)

    if result > 0:
        question = message.text

        answer = await OpenAiTools.get_chatgpt(question)

        if answer:
            await message.answer(
                text=answer,
                reply_markup=reply_markup,
            )
            result -= len(await asyncio.get_running_loop().run_in_executor(None, encoding.encode, question + answer))
            if result > 0:
                await DataBase.set_chatgpt(user_id, result)
            else:
                await DataBase.set_chatgpt(user_id, 0)
        else:
            await message.answer(
                text="❌Ваш запрос активировал фильтры безопасности API и не может быть обработан. Пожалуйста, измените подсказку и повторите попытку.",
                reply_markup=reply_markup,
            )

    else:
        await message.answer(
            text="❎У вас 0 токенов ChatGPT. Вам необходимо купить их, чтобы использовать ChatGPT.",
            reply_markup=reply_markup,
        )
    await state.set_state(States.CHATGPT_STATE)


# Answer Handling
@dp.message(States.DALL_E_STATE, F.text)
async def dall_e_answer_handler(message: types.Message, state: FSMContext):
    button = [[KeyboardButton(text="🔙Назад")]]
    reply_markup = ReplyKeyboardMarkup(
        keyboard=button, resize_keyboard=True
    )

    user_id = message.from_user.id
    result = await DataBase.get_dalle(user_id)

    if result > 0:
        question = message.text

        prompt = await translator.translate(question, targetlang='en')

        answer = await OpenAiTools.get_dalle(prompt.text)

        if answer:
            await message.answer_photo(
                photo=answer,
                reply_markup=reply_markup,
                caption=question,
            )
            result -= 1
            await DataBase.set_dalle(user_id, result)
        else:
            await message.answer(
                text="❌Ваш запрос активировал фильтры безопасности API и не может быть обработан. Пожалуйста, измените подсказку и повторите попытку.",
                reply_markup=reply_markup,
            )
    else:
        await message.answer(
            text="❎У вас 0 генераций изображений DALL·E. Вам необходимо купить их, чтобы использовать DALL·E.",
            reply_markup=reply_markup,
        )
    await state.set_state(States.DALL_E_STATE)


# Answer Handling
@dp.message(States.STABLE_STATE, F.text)
async def stable_answer_handler(message: types, state: FSMContext):
    button = [[KeyboardButton(text="🔙Назад")]]
    reply_markup = ReplyKeyboardMarkup(
        keyboard=button, resize_keyboard=True
    )

    user_id = message.from_user.id
    result = await DataBase.get_stable(user_id)

    if result > 0:

        question = message.text

        prompt = await translator.translate(question, targetlang='en')

        path = await asyncio.get_running_loop().run_in_executor(None, StableDiffusion.get_stable, prompt.text)

        if path:
            await message.answer_photo(
                photo=FSInputFile(path),
                reply_markup=reply_markup,
                caption=question,
            )
            await remove(path)
            result -= 1
            await DataBase.set_stable(user_id, result)
        else:
            await message.answer(
                text="❌Ваш запрос активировал фильтры безопасности API и не может быть обработан. Пожалуйста, измените подсказку и повторите попытку.",
                reply_markup=reply_markup,
            )
    else:
        await message.answer(
            text="❎У вас 0 генераций изображений STABLE DIFFUSION. Вам нужно купить их, чтобы использовать Stable Diffusion.",
            reply_markup=reply_markup,
        )
    await state.set_state(States.STABLE_STATE)


# Displays information about user
@dp.message(States.ENTRY_STATE, F.text.regexp(r'^👤Мой аккаунт | 💰Купить$'))
@dp.message(States.PURCHASE_STATE, F.text.regexp(r'^🔙Назад'))
async def display_info(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    result = await DataBase.get_userinfo(user_id)

    button = [[KeyboardButton(text="💰Купить токены и генерации")], [KeyboardButton(text="🔙Назад")]]
    reply_markup = ReplyKeyboardMarkup(
        keyboard=button, resize_keyboard=True
    )
    await message.answer(
        text=f"У тебя есть: \n 💭{result[2]} ChatGPT токенов \n 🌄{result[3]} DALL·E генераций изображений \n 🌅{result[4]} Stable Diffusion генераций изображений  \n 💸 Ты можешь купить больше с помощью криптовалюты",
        reply_markup=reply_markup,
    )
    await state.set_state(States.INFO_STATE)


# Displays goods
@dp.message(States.INFO_STATE, F.text.regexp(r'^💰Купить токены и генерации$'))
@dp.message(States.PURCHASE_CHATGPT_STATE, F.text.regexp(r'^🔙Назад$'))
@dp.message(States.PURCHASE_DALL_E_STATE, F.text.regexp(r'^🔙Назад$'))
@dp.message(States.PURCHASE_STABLE_STATE, F.text.regexp(r'^🔙Назад$'))
async def purchase(message: types.Message, state: FSMContext):
    button = [[KeyboardButton(text="100K ChatGPT токенов - 5 USD💵")],
              [KeyboardButton(text="100 DALL·E генераций изображений - 5 USD💵")],
              [KeyboardButton(text="100 Stable Diffusion генерации изображений - 5 USD💵")],
              [KeyboardButton(text="🔙Назад")]]
    reply_markup = ReplyKeyboardMarkup(
        keyboard=button, resize_keyboard=True
    )
    await message.answer(
        text="Выберите товар: 👇",
        reply_markup=reply_markup,
    )
    await state.set_state(States.PURCHASE_STATE)


# Displays cryptocurrencies
@dp.message(States.PURCHASE_STATE, F.text.regexp(r'^100K ChatGPT токенов - 5 USD💵$'))
@dp.message(States.PURCHASE_STATE, F.text.regexp(r'^100 DALL·E генераций изображений - 5 USD💵$'))
@dp.message(States.PURCHASE_STATE, F.text.regexp(r'^100 Stable Diffusion генераций изображений - 5 USD💵$'))
async def currencies(message: types.Message, state: FSMContext):
    buttons = [
        [KeyboardButton(text="💲USDT"),
         KeyboardButton(text="💲TON")],
        [KeyboardButton(text="💲BTC"),
         KeyboardButton(text="💲ETH")],
        [KeyboardButton(text="🔙Назад")]
    ]
    keyboard = ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True
    )
    await message.answer(
        text="Выберите валюту: 👇",
        reply_markup=keyboard,
    )
    product = message.text
    if product == "100K ChatGPT токенов - 5 USD💵":
        await state.set_state(States.PURCHASE_CHATGPT_STATE)
    elif product == "100 DALL·E генераций изображений - 5 USD💵":
        await state.set_state(States.PURCHASE_DALL_E_STATE)
    elif product == "100 Stable Diffusion генераций изображений - 5 USD💵":
        await state.set_state(States.PURCHASE_STABLE_STATE)


# Makes invoice and displays it
@dp.message(States.PURCHASE_CHATGPT_STATE, F.text.regexp(r'^💲USDT$'))
@dp.message(States.PURCHASE_CHATGPT_STATE, F.text.regexp(r'^💲TON$'))
@dp.message(States.PURCHASE_CHATGPT_STATE, F.text.regexp(r'^💲BTC$'))
@dp.message(States.PURCHASE_CHATGPT_STATE, F.text.regexp(r'^💲ETH$'))
@dp.message(States.PURCHASE_DALL_E_STATE, F.text.regexp(r'^💲USDT$'))
@dp.message(States.PURCHASE_DALL_E_STATE, F.text.regexp(r'^💲TON$'))
@dp.message(States.PURCHASE_DALL_E_STATE, F.text.regexp(r'^💲BTC$'))
@dp.message(States.PURCHASE_DALL_E_STATE, F.text.regexp(r'^💲ETH$'))
@dp.message(States.PURCHASE_STABLE_STATE, F.text.regexp(r'^💲USDT$'))
@dp.message(States.PURCHASE_STABLE_STATE, F.text.regexp(r'^💲TON$'))
@dp.message(States.PURCHASE_STABLE_STATE, F.text.regexp(r'^💲BTC$'))
@dp.message(States.PURCHASE_STABLE_STATE, F.text.regexp(r'^💲ETH$'))
async def buy(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    currency = message.text
    invoice_url, invoice_id = await CryptoPay.create_invoice(5, currency[1:])
    current_state = await state.get_state()
    product = ''
    if current_state == States.PURCHASE_CHATGPT_STATE:
        product = '100K ChatGPT токенов - 5 USD💵'
        await DataBase.new_order(invoice_id, user_id, 'chatgpt')
    elif current_state == States.PURCHASE_DALL_E_STATE:
        product = '100 DALL·E генераций изображений - 5 USD💵'
        await DataBase.new_order(invoice_id, user_id, 'dall_e')
    elif current_state == States.PURCHASE_STABLE_STATE:
        product = '100 Stable Diffusion генераций изображений - 5 USD💵'
        await DataBase.new_order(invoice_id, user_id, 'stable')
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💰Купить", url=invoice_url),
             InlineKeyboardButton(text="☑️Проверить", callback_data=str(invoice_id))],
        ]
    )
    await message.answer(
        text=f"🪙Товар: {product} \n 💳Если вы хотите оплатить, нажмите кнопку «Купить», нажмите кнопку «Старт» в Крипто-боте и следуйте инструкциям \n ❗Учитывайте комиссию сети \n ☑️После оплаты вам следует нажать кнопку «Проверить», чтобы проверить платеж \n Если вы не хотите платить нажмите кнопку «Назад»: 👇",
        reply_markup=keyboard,
    )


# Checks payment
@dp.callback_query()
async def keyboard_callback(callback_query: types.CallbackQuery):
    query = callback_query
    invoice_id = int(query.data)
    result = await DataBase.get_orderdata(invoice_id)
    if result:
        status = await CryptoPay.get_status(invoice_id)
        if status == "active":
            await query.answer("⌚️Мы еще не получили вашу оплату")
        elif status == "paid":
            if result[1] == 'chatgpt':
                await DataBase.update_chatgpt(result[0], invoice_id)
                await query.answer("✅Успешная оплата, токены добавлены на ваш счет")
            elif result[1] == 'dall_e':
                await DataBase.update_dalle(result[0], invoice_id)
                await query.answer("✅Успешная оплата, генерации изображений добавлены в ваш аккаунт")
            elif result[1] == 'stable':
                await DataBase.update_stable(result[0], invoice_id)
                await query.answer("✅Успешная оплата, генерации изображений добавлены в ваш аккаунт")
        elif status == "expired":
            await query.answer("❎Срок платежа истек, создайте новый платеж.")
    else:
        await query.answer("✅Вы уже получили свою покупку")


async def main():
    await DataBase.open_pool()
    await dp.start_polling(bot)


if __name__ == '__main__':
    load_dotenv()
    translator = Translator()
    bot = Bot(token=getenv("TELEGRAM_BOT_TOKEN"))
    encoding = encoding_for_model("gpt-3.5-turbo")
    asyncio.run(main())
