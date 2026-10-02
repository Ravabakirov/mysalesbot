import asyncio
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime

from database import Database

BOT_TOKEN = "8613310069:AAHbfkRBJ2U_a9SZhb4PwMoSDCGluQy7kAA"  # BotFather tokeningiz
ADMIN_ID = 1081311978              # Telegram ID'ingiz

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
db = Database()

# FSM Holatlari
class ClientState(StatesGroup):
    fullname = State()
    phone = State()
    details = State()
    status_choice = State()
    buy_date = State()

class FilterDateState(StatesGroup):
    target_date = State()

class UpdateStatusState(StatesGroup):
    client_id = State()
    new_buy_date = State()

# Klaviatura
def main_menu():
    kb = [
        [KeyboardButton(text="➕ Yangi lid qo'shish")],
        [KeyboardButton(text="📅 Bugungi klientlar"), KeyboardButton(text="📞 Tel ko'tarmaganlar")],
        [KeyboardButton(text="📆 Sanalar bo'yicha filtr"), KeyboardButton(text="📊 Barcha aktiv lidlar")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def status_keyboard():
    kb = [
        [InlineKeyboardButton(text="📅 Shu kuni olaman dedi", callback_data="status_will_buy")],
        [InlineKeyboardButton(text="📞 Tel ko'tarmadi", callback_data="status_no_answer")],
        [InlineKeyboardButton(text="❌ Rad etdi / Oylamoqda", callback_data="status_other")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

# --- COMMANDS ---

@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Kechirasiz, bu bot shaxsiy foydalanish uchun moslangan.")
        return
    await message.answer("Xush kelibsiz! Sotuv operatsiyalarini boshqarish menyusi:", reply_markup=main_menu())

# --- YANGI LID QO'SHISH ---

@dp.message(F.text == "➕ Yangi lid qo'shish")
async def start_add_client(message: types.Message, state: FSMContext):
    await state.set_state(ClientState.fullname)
    await message.answer("Mijozning **Ism va Familiyasi**ni kiriting:")

@dp.message(ClientState.fullname)
async def process_fullname(message: types.Message, state: FSMContext):
    await state.update_data(fullname=message.text)
    await state.set_state(ClientState.phone)
    await message.answer("Mijozning **Telefon raqami**ni kiriting:")

@dp.message(ClientState.phone)
async def process_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await state.set_state(ClientState.details)
    await message.answer("Nima bo'lganini / qiziqqan mahsuloti haqida **qisqacha ma'lumot** kiriting:")

@dp.message(ClientState.details)
async def process_details(message: types.Message, state: FSMContext):
    await state.update_data(details=message.text)
    await state.set_state(ClientState.status_choice)
    await message.answer("Mijoz holatini (statusini) tanlang:", reply_markup=status_keyboard())

@dp.callback_query(ClientState.status_choice, F.data == "status_no_answer")
async def status_no_answer_selected(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    db.add_client(fullname=data["fullname"], phone=data["phone"], details=data["details"], status="no_answer")
    await state.clear()
    await call.message.edit_text("✅ Mijoz **'Tel ko'tarmaganlar'** ro'yxatiga saqlandi!")

@dp.callback_query(ClientState.status_choice, F.data == "status_other")
async def status_other_selected(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    db.add_client(fullname=data["fullname"], phone=data["phone"], details=data["details"], status="other")
    await state.clear()
    await call.message.edit_text("✅ Mijoz saqlandi.")

@dp.callback_query(ClientState.status_choice, F.data == "status_will_buy")
async def status_will_buy_selected(call: types.CallbackQuery, state: FSMContext):
    await state.set_state(ClientState.buy_date)
    await call.message.edit_text("Mijoz qaysi kuni sotib olmoqchi? Sanani `YYYY-MM-DD` formatida kiriting (Masalan: `2026-10-15`):", parse_mode="Markdown")

@dp.message(ClientState.buy_date)
async def process_buy_date(message: types.Message, state: FSMContext):
    data = await state.get_data()
    buy_date = message.text.strip()
    db.add_client(fullname=data["fullname"], phone=data["phone"], details=data["details"], status="will_buy", buy_date=buy_date)
    await state.clear()
    await message.answer(f"✅ Mijoz saqlandi! Belgilangan sana: **{buy_date}**", parse_mode="Markdown")

# --- LISTLAR VA STATUSNI YANGILASH ---

@dp.message(F.text == "📞 Tel ko'tarmaganlar")
async def show_no_answer_clients(message: types.Message):
    clients = db.get_no_answer_clients()
    if not clients:
        await message.answer("️'Telefon ko'tarmagan' mijozlar mavjud emas.")
        return

    for c in clients:
        btn = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🔄 Zakaz berdi (Statusni yangilash)", callback_data=f"update_{c[0]}")
        ]])
        text = f"👤 **{c[1]}**\n📞 Tel: `{c[2]}`\n📝 Tafsilot: {c[3]}"
        await message.answer(text, reply_markup=btn, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("update_"))
async def start_update_status(call: types.CallbackQuery, state: FSMContext):
    client_id = int(call.data.split("_")[1])
    await state.update_data(client_id=client_id)
    await state.set_state(UpdateStatusState.new_buy_date)
    await call.message.answer("Mijoz qaysi kuni oladigan bo'ldi? Sanani `YYYY-MM-DD` formatida kiriting (Masalan: `2026-10-10`):", parse_mode="Markdown")

@dp.message(UpdateStatusState.new_buy_date)
async def process_new_buy_date(message: types.Message, state: FSMContext):
    data = await state.get_data()
    client_id = data["client_id"]
    new_date = message.text.strip()
    
    db.update_client_status(client_id, new_status="will_buy", buy_date=new_date)
    await state.clear()
    await message.answer(f"✅ Mijoz statusi yangilandi! Endi u **{new_date}** kungi zakazlar ro'yxatida ko'rinadi.", parse_mode="Markdown")

@dp.message(F.text == "📅 Bugungi klientlar")
async def show_today_clients(message: types.Message):
    today = datetime.now().strftime("%Y-%m-%d")
    clients = db.get_clients_by_date(today)
    if not clients:
        await message.answer(f"Bugun ({today}) uchun mo'ljallangan mijozlar topilmadi.")
        return

    text = f"📅 **Bugun ({today}) sotib oladigan mijozlar:**\n\n"
    for c in clients:
        text += f"👤 **{c[1]}**\n📞 Tel: `{c[2]}`\n📝 Tafsilot: {c[3]}\n──────────────────\n"
    await message.answer(text, parse_mode="Markdown")

@dp.message(F.text == "📆 Sanalar bo'yicha filtr")
async def request_filter_date(message: types.Message, state: FSMContext):
    await state.set_state(FilterDateState.target_date)
    await message.answer("Qaysi kungi mijozlarni ko'rmoqchisiz? Sanani `YYYY-MM-DD` formatida kiriting:", parse_mode="Markdown")

@dp.message(FilterDateState.target_date)
async def process_filter_date(message: types.Message, state: FSMContext):
    target_date = message.text.strip()
    clients = db.get_clients_by_date(target_date)
    await state.clear()
    
    if not clients:
        await message.answer(f"Sana: **{target_date}** bo'yicha mijozlar topilmadi.", parse_mode="Markdown")
        return

    text = f"📆 **{target_date} kuni sotib oladigan mijozlar:**\n\n"
    for c in clients:
        text += f"👤 **{c[1]}**\n📞 Tel: `{c[2]}`\n📝 Tafsilot: {c[3]}\n──────────────────\n"
    await message.answer(text, parse_mode="Markdown")

@dp.message(F.text == "📊 Barcha aktiv lidlar")
async def show_all_clients(message: types.Message):
    clients = db.get_all_active_clients()
    if not clients:
        await message.answer("Hozircha bazada lidlar yo'q.")
        return

    text = "📊 **Barcha lidlar:**\n\n"
    for c in clients:
        status_text = "📞 Tel ko'tarmagan" if c[3] == "no_answer" else (f"📅 {c[4]} kuni oladi" if c[3] == "will_buy" else "Boshqa")
        text += f"👤 **{c[1]}** | `{c[2]}`\nStatus: {status_text}\n──────────────────\n"
    await message.answer(text, parse_mode="Markdown")

async def main():
    logging.basicConfig(level=logging.INFO)
    print("Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())