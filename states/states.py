from aiogram.fsm.state import State, StatesGroup

class BotStates(StatesGroup):
    IDLE = State()
    THUMB_WAITING_PHOTO = State()
    THUMB_WAITING_VIDEOS = State()
    THUMB_PROCESSING = State()
    CAP_WAITING_VIDEO = State()
    CAP_WAITING_CAPTION = State()
    CAP_PROCESSING = State()

    # Admin FSM states
    ADMIN_SET_FS = State()
    ADMIN_BROADCAST = State()
    ADMIN_BAN_USER = State()
    ADMIN_UNBAN_USER = State()
    ADMIN_GET_USER = State()
